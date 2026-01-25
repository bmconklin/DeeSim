import os
import json
import requests
import inspect
from typing import List, Dict, Any, Optional, get_type_hints

# Constants
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/chat"
DEFAULT_LOCAL_MODEL = "llama3"

def python_type_to_json_type(py_type):
    """Maps Python types to JSON schema types."""
    if py_type == str: return "string"
    if py_type == int: return "integer"
    if py_type == float: return "number"
    if py_type == bool: return "boolean"
    if py_type == list: return "array"
    if py_type == dict: return "object"
    # Basic fallback for Optional/Union types - simplify to string for robustness or try to extract
    return "string"

def convert_to_ollama_tool(func):
    """Converts a Python function to an OpenAI/Ollama JSON schema tool definition."""
    type_hints = get_type_hints(func)
    signature = inspect.signature(func)
    
    properties = {}
    required = []
    
    for param_name, param in signature.parameters.items():
        if param_name == 'self': continue
        
        param_type = type_hints.get(param_name, str)
        param_desc = "Parameter" # We could parse docstrings here for better descriptions
        
        properties[param_name] = {
            "type": python_type_to_json_type(param_type),
            "description": param_desc 
        }
        
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
            
    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }
    return schema

class LocalChatSession:
    """
    A compatible wrapper for Ollama/Local LLM that mimics google.genai.chats.Chat
    """
    def __init__(self, model: str, history: List[Dict], system_instruction: str, tools: List[Any]):
        self.model = model
        self.history = history if history else [] # Format: [{"role": "user", "parts": ["text"]}, ...]
        self.system_instruction = system_instruction
        self.api_url = os.environ.get("OLLAMA_HOST", OLLAMA_DEFAULT_URL)
        
        # Tool Setup
        self.tool_map = {f.__name__: f for f in tools}
        self.ollama_tools = [convert_to_ollama_tool(f) for f in tools]
        
        # Normalize history to Ollama format
        self.context_window = []
        if self.system_instruction:
            self.context_window.append({"role": "system", "content": self.system_instruction})
            
        for msg in self.history:
             # Basic conversion
             role = msg.get("role", "user")
             if role == "model": role = "assistant"
             
             parts = msg.get("parts", [])
             content = ""
             if isinstance(parts, list):
                 content = " ".join([str(p) for p in parts])
             else:
                 content = str(parts)
                 
             self.context_window.append({"role": role, "content": content})

    def send_message(self, content_parts: List[Any], max_turns=5) -> Any:
        """
        Sends a message to the local LLM and handles tool execution loop.
        """
        # 1. Parse Input
        user_text = ""
        for part in content_parts:
            if isinstance(part, str):
                user_text += part + "\n"
            
        self.context_window.append({"role": "user", "content": user_text})
        self.history.append({"role": "user", "parts": [user_text]}) # Keep synced
        
        current_turn = 0
        final_ai_text = ""
        
        while current_turn < max_turns:
            current_turn += 1
            
            # 2. Call API
            payload = {
                "model": self.model,
                "messages": self.context_window,
                "stream": False,
                "tools": self.ollama_tools # Attach tools
            }
            
            try:
                print(f"📡 Sending to Local LLM ({self.api_url})... [Turn {current_turn}]")
                response = requests.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                message = data.get("message", {})
                ai_text = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
                
                # If content exists, capture it (Model might think aloud before calling tool)
                if ai_text:
                    final_ai_text = ai_text # Update final text
                    print(f"🤖 AI Thought: {ai_text[:50]}...")
                
                # 3. Handle Tool Calls
                if tool_calls:
                    self.context_window.append(message) # Add the assistant's request to history
                    
                    for tool_call in tool_calls:
                        func_name = tool_call.get("function", {}).get("name")
                        args = tool_call.get("function", {}).get("arguments", {})
                        
                        print(f"🛠️ Tool Call: {func_name}({args})")
                        
                        if func_name in self.tool_map:
                            try:
                                func = self.tool_map[func_name]
                                # Execute Python Function
                                result = func(**args)
                                tool_output = str(result)
                            except Exception as e:
                                tool_output = f"Error executing {func_name}: {e}"
                        else:
                            tool_output = f"Error: Tool {func_name} not found."
                            
                        print(f"   -> Result: {tool_output[:50]}...")
                        
                        # Add Result to History
                        self.context_window.append({
                            "role": "tool",
                            "name": func_name,
                            "content": tool_output
                        })
                    
                    # Continue Loop -> Send tool outputs back to LLM
                    continue
                
                else:
                    # No tools, just text response. We are done.
                    self.context_window.append({"role": "assistant", "content": ai_text})
                    self.history.append({"role": "model", "parts": [ai_text]})
                    
                    class MockResponse:
                        def __init__(self, text):
                            self.text = text
                    return MockResponse(ai_text)
                    
            except Exception as e:
                return MockResponse(f"Local LLM Error: {e}")
                
        return MockResponse("Max turns reached without final response.")

    def get_history(self):
        return self.history


class GoogleChatSession:
    """
    A wrapper to keep the Google Client alive alongside the Chat Session.
    """
    def __init__(self, api_key: str, model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
        # Import lazily to avoid heavy deps if running local-only
        import google.genai as genai
        from google.genai import types
        
        self.client = genai.Client(api_key=api_key)
        self.chat = self.client.chats.create(
            model=model_name,
            history=history,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
    def send_message(self, content_parts: List[Any]) -> Any:
        return self.chat.send_message(content_parts)
    
    def get_history(self):
        # Return history from the underlying chat object
        # The new SDK uses _curated_history for the message list
        return self.chat._curated_history

def get_chat_session(model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
    """
    Factory to return either a Google Chat or a Local Chat.
    """
    google_key = os.environ.get("GOOGLE_API_KEY")
    
    if google_key:
        return GoogleChatSession(google_key, model_name, history, tools, system_instruction)
    else:
        # Use Local LLM
        local_model = os.environ.get("LOCAL_MODEL_NAME", DEFAULT_LOCAL_MODEL)
        print(f"🔌 GOOGLE_API_KEY not found. Switching to Local LLM: {local_model}")
        return LocalChatSession(local_model, history, system_instruction, tools)
