import os
import json
import requests
import inspect
from typing import List, Dict, Any, Optional, get_type_hints

# Constants
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/chat"
DEFAULT_LOCAL_MODEL = "llama3"
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

class MockResponse:
    def __init__(self, text):
        self.text = text

def python_type_to_json_type(py_type):
    """Maps Python types to JSON schema types."""
    if py_type == str: return "string"
    if py_type == int: return "integer"
    if py_type == float: return "number"
    if py_type == bool: return "boolean"
    if py_type == list: return "array"
    if py_type == dict: return "object"
    # Basic fallback for Optional/Union types
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
        param_desc = "Parameter" 
        
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

def convert_to_anthropic_tool(func):
    """Converts a Python function to Anthropic tool definition."""
    # Anthropic uses nearly identical schema to OpenAI now, but strictly requires input_schema
    # Structure: { "name": "...", "description": "...", "input_schema": { ... } }
    
    ollama_schema = convert_to_ollama_tool(func)["function"]
    
    return {
        "name": ollama_schema["name"],
        "description": ollama_schema["description"],
        "input_schema": ollama_schema["parameters"]
    }

class LocalChatSession:
    """
    A compatible wrapper for Ollama/Local LLM.
    """
    def __init__(self, model: str, history: List[Dict], system_instruction: str, tools: List[Any]):
        self.model = model
        self.history = history if history else [] 
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
             role = msg.get("role", "user")
             if role == "model": role = "assistant"
             
             parts = msg.get("parts", [])
             content = ""
             if isinstance(parts, list):
                 content = " ".join([str(p) for p in parts])
             else:
                 content = str(parts)
                 
             self.context_window.append({"role": role, "content": content})

    def send_message(self, content_parts: List[Any], max_turns=5, timeout=None) -> Any:
        # 1. Parse Input
        user_text = ""
        for part in content_parts:
            if isinstance(part, str):
                user_text += part + "\n"
            
        self.context_window.append({"role": "user", "content": user_text})
        self.history.append({"role": "user", "parts": [user_text]}) 
        
        current_turn = 0
        final_ai_text = ""
        
        while current_turn < max_turns:
            current_turn += 1
            
            # 2. Call API
            payload = {
                "model": self.model,
                "messages": self.context_window,
                "stream": False,
                "tools": self.ollama_tools
            }
            
            try:
                print(f"📡 Sending to Local LLM ({self.api_url})... [Turn {current_turn}]")
                response = requests.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                message = data.get("message", {})
                ai_text = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
                
                if ai_text:
                    final_ai_text = ai_text 
                    print(f"🤖 AI Thought: {ai_text[:50]}...")
                
                # 3. Handle Tool Calls
                if tool_calls:
                    self.context_window.append(message) 
                    
                    for tool_call in tool_calls:
                        func_name = tool_call.get("function", {}).get("name")
                        args = tool_call.get("function", {}).get("arguments", {})
                        
                        print(f"🛠️ Tool Call: {func_name}({args})")
                        
                        if func_name in self.tool_map:
                            try:
                                func = self.tool_map[func_name]
                                result = func(**args)
                                tool_output = str(result)
                            except Exception as e:
                                tool_output = f"Error executing {func_name}: {e}"
                        else:
                            tool_output = f"Error: Tool {func_name} not found."
                            
                        print(f"   -> Result: {tool_output[:50]}...")
                        
                        self.context_window.append({
                            "role": "tool",
                            "name": func_name,
                            "content": tool_output
                        })
                    
                    continue
                
                else:
                    self.context_window.append({"role": "assistant", "content": ai_text})
                    self.history.append({"role": "model", "parts": [ai_text]})
                    
                    return MockResponse(ai_text)
                    
            except Exception as e:
                return MockResponse(f"Local LLM Error: {e}")
                
        return MockResponse("Max turns reached without final response.")

    def get_history(self):
        return self.history


class ClaudeChatSession:
    """
    Wrapper for Anthropic's Claude API.
    """
    def __init__(self, api_key: str, model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model_name or DEFAULT_CLAUDE_MODEL
        self.system = system_instruction
        self.history = history if history else []
        
        self.tool_map = {f.__name__: f for f in tools}
        self.claude_tools = [convert_to_anthropic_tool(f) for f in tools]
        
        # Normalize History for Claude
        # Claude strictly alternates User/Assistant. 
        # We need to ensure valid conversation structure.
        self.messages = []
        for msg in self.history:
             role = msg.get("role", "user")
             if role == "model": role = "assistant"
             
             parts = msg.get("parts", [])
             content = ""
             if isinstance(parts, list):
                 content = " ".join([str(p) for p in parts])
             else:
                 content = str(parts)
            
             self.messages.append({"role": role, "content": content})


    def send_message(self, content_parts: List[Any], max_turns=10, timeout=None) -> Any:
        # 1. Parse Input
        user_text = ""
        for part in content_parts:
            if isinstance(part, str):
                user_text += part + "\n"
        
        self.messages.append({"role": "user", "content": user_text})
        self.history.append({"role": "user", "parts": [user_text]})
        
        current_turn = 0
        final_text = ""
        
        while current_turn < max_turns:
            current_turn += 1
            print(f"📡 Sending to Claude ({self.model})... [Turn {current_turn}]")
            
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=self.system,
                    messages=self.messages,
                    tools=self.claude_tools
                )
            except Exception as e:
                return type('MockResponse', (object,), {"text": f"Claude Error: {e}"})()

            # Process Response
            content_blocks = response.content
            
            # Helper to append assistant response to our message list in correct format
            # Claude expects the *exact* list of blocks returned for correct history
            self.messages.append({
                "role": "assistant",
                "content": content_blocks
            })
            
            tool_results = []
            has_tool_use = False
            
            text_part = ""
            
            for block in content_blocks:
                if block.type == "text":
                    print(f"🤖 Claude Thought: {block.text[:50]}...")
                    text_part += block.text
                    final_text += block.text
                
                elif block.type == "tool_use":
                    has_tool_use = True
                    func_name = block.name
                    args = block.input
                    tool_use_id = block.id
                    
                    print(f"🛠️ Tool Call: {func_name}({args})")
                    
                    if func_name in self.tool_map:
                        try:
                            func = self.tool_map[func_name]
                            result = func(**args)
                            tool_output = str(result)
                        except Exception as e:
                            tool_output = f"Error executing {func_name}: {e}"
                    else:
                        tool_output = f"Error: Tool {func_name} not found."
                        
                    print(f"   -> Result: {tool_output[:50]}...")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_output
                    })
            
            if has_tool_use:
                # Add tool results to conversation and loop
                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })
                # Loop continues
            else:
                # Done
                self.history.append({"role": "model", "parts": [final_text]})
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                return MockResponse(final_text)

        return type('MockResponse', (object,), {"text": "Max turns reached."})()

    def get_history(self):
        return self.history


class GoogleChatSession:
    """
    A wrapper to keep the Google Client alive alongside the Chat Session.
    """
    def __init__(self, api_key: str, model_name: str, history: List[Dict], tools: List[Any], system_instruction: str, vertex_project: str = None, vertex_location: str = "us-central1"):
        # Import lazily to avoid heavy deps if running local-only
        import google.genai as genai
        from google.genai import types
        import httpx
        
        # Robust Timeout Configuration
        # Connect: 60s (Handshake)
        # Read/Write: 120s (Generation)
        timeout_config = httpx.Timeout(120.0, connect=60.0)

        if vertex_project:
            print(f"☁️ Connecting to Vertex AI (Project: {vertex_project}, Loc: {vertex_location})")
            self.client = genai.Client(
                vertexai=True, 
                project=vertex_project, 
                location=vertex_location,
                http_options=types.HttpOptions(
                    timeout=None, # Disable top-level timeout to avoid conflicts
                    client_args={"timeout": timeout_config} 
                )
            )
        else:
            self.client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=None,
                    client_args={"timeout": timeout_config}
                )
            )
            
        self.chat = self.client.chats.create(
            model=model_name,
            history=history,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
    def send_message(self, content_parts: List[Any], timeout: int = None) -> Any:
        config = None
        if timeout:
            from google.genai import types
            import httpx
            # Pass timeout in client_args to be safe
            # Determine if timeout matches our default 90/120 pattern or is custom
            t_val = float(timeout)
            t_conf = httpx.Timeout(t_val, connect=60.0)
            
            config = types.GenerateContentConfig(
                http_options=types.HttpOptions(
                    timeout=None,
                    client_args={"timeout": t_conf}
                )
            )
        return self.chat.send_message(content_parts, config=config)
    
    def get_history(self):
        # Return history from the underlying chat object
        # The new SDK uses _curated_history for the message list
        return self.chat._curated_history

        return self.chat._curated_history

def resolve_model_config():
    """
    Determines the active provider and model name based on environment variables.
    Returns: (provider_type, model_name)
    """
    google_key = os.environ.get("GOOGLE_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    vertex_project = os.environ.get("GOOGLE_VERTEX_PROJECT")
    
    # Priority 1: Force Claude
    if os.environ.get("FORCE_CLAUDE") and anthropic_key:
        return "claude", os.environ.get("CLAUDE_MODEL_NAME", DEFAULT_CLAUDE_MODEL)
        
    # Priority 2: Google (Key OR Vertex)
    if google_key or vertex_project:
        return "google", os.environ.get("MODEL_NAME", "gemini-1.5-flash")
    
    # Priority 3: Claude (if no Google)
    if anthropic_key:
        return "claude", os.environ.get("CLAUDE_MODEL_NAME", DEFAULT_CLAUDE_MODEL)
        
    # Priority 4: Local
    return "local", os.environ.get("LOCAL_MODEL_NAME", DEFAULT_LOCAL_MODEL)

def get_chat_session(model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
    """
    Factory to return either a Google Chat, Claude Chat, or a Local Chat.
    Uses resolve_model_config for defaults, but allows overrides if model_name is passed explicitly 
    (though currently model_name arg is often just the default env var value).
    """
    provider, config_model = resolve_model_config()
    
    # If the passed model_name matches the 'gemini-1.5-flash' default we setup in other files, 
    # we prefer the resolved config_model which might be a Local/Claude model.
    # To avoid confusion, let's rely on the provider logic.
    
    google_key = os.environ.get("GOOGLE_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    vertex_project = os.environ.get("GOOGLE_VERTEX_PROJECT")
    
    if provider == "claude":
        print(f"🧠 Switching to Claude: {config_model}")
        return ClaudeChatSession(anthropic_key, config_model, history, tools, system_instruction)
        
    if provider == "google":
        vertex_loc = os.environ.get("GOOGLE_VERTEX_LOCATION", "us-central1")
        # Use the config_model as authoritative source of truth for the name
        return GoogleChatSession(google_key, config_model, history, tools, system_instruction, vertex_project, vertex_loc)
        
    if provider == "local":
        print(f"🔌 Switching to Local LLM: {config_model}")
        return LocalChatSession(config_model, history, system_instruction, tools)

    raise ValueError("Unknown provider configuration")

