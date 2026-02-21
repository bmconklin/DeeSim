import os
import json
import litellm
from typing import List, Dict, Any

# Constants
DEFAULT_LOCAL_MODEL = "ollama/llama3"
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20240620"
DEFAULT_GEMINI_MODEL = "gemini/gemini-1.5-pro-latest"

# Optional: suppress overly verbose litellm logging if desired
litellm.suppress_debug_info = True

class MockResponse:
    def __init__(self, text):
        self.text = text

class ChatSession:
    """
    A unified wrapper for Anthropic, Google, and Local LLMs using LiteLLM.
    """
    def __init__(self, model: str, history: List[Dict], tools: List[Any], system_instruction: str):
        self.model = model
        self.system = system_instruction
        self.tool_map = {f.__name__: f for f in tools}
        
        # Use litellm's native utility to automatically parse python functions into OpenAI schemas
        from litellm.utils import function_to_dict
        self.tools = [{"type": "function", "function": function_to_dict(f)} for f in tools] if tools else None
        
        # Normalize History exactly to OpenAI format (which LiteLLM translates to others)
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": self.system})
            
        for msg in history:
            role = msg.get("role", "user")
            # Map Gemini 'model' to standard 'assistant'
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
        
        current_turn = 0
        final_text = ""
        
        while current_turn < max_turns:
            current_turn += 1
            print(f"📡 Sending to {self.model}... [Turn {current_turn}]")
            
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    timeout=timeout,
                    max_tokens=2048
                )
            except Exception as e:
                return MockResponse(f"LLM Error ({self.model}): {e}")

            # Process Response
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = message.tool_calls or []
            
            # Append AI response to messages array to maintain valid context window
            self.messages.append(message.model_dump())
            
            if content:
                final_text += content

            # 3. Handle Tool Calls
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    # Parse arguments string into dict
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                        
                    print(f"🛠️ Tool Call: {func_name}({args})")
                    
                    if func_name in self.tool_map:
                        import src.dm_utils as dm_utils
                        try:
                            func = self.tool_map[func_name]
                            result = func(**args)
                            tool_output = str(result)
                            dm_utils.log_system_tool_call(func_name, args, tool_output)
                        except Exception as e:
                            tool_output = f"Error executing {func_name}: {e}"
                            dm_utils.log_system_tool_call(func_name, args, tool_output)
                    else:
                        tool_output = f"Error: Tool {func_name} not found."
                        
                    print(f"   -> Result: {tool_output[:50]}...")
                    
                    # Add tool results to conversation history array
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": tool_output
                    })
                
                # Loop continues back to litellm.completion() with the tool responses appended
                continue
                
            else:
                # Output complete
                return MockResponse(final_text)

        return MockResponse(final_text + "\n\n[Error: Max tool turns reached]")

    def get_history(self):
        # Filter out system and tool messages to just keep the narrative for state saving
        # Convert it back to native "parts" schema for compatibility with existing code
        curated = []
        for msg in self.messages:
            if msg.get("role") in ["user", "assistant"]:
                role = "model" if msg["role"] == "assistant" else "user"
                content = msg.get("content", "")
                
                # Deduplicate sequential messages of the same role (required by Gemini)
                if curated and curated[-1]["role"] == role:
                    curated[-1]["parts"][0] += f"\n\n{content}"
                else:
                    curated.append({"role": role, "parts": [content]})
                    
        return curated

def resolve_model_config():
    """
    Determines the active provider AND mapping for liteLLM.
    """
    google_key = os.environ.get("GOOGLE_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Priority 1: Force Claude
    if os.environ.get("FORCE_CLAUDE") and anthropic_key:
        return os.environ.get("CLAUDE_MODEL_NAME", DEFAULT_CLAUDE_MODEL)
        
    # Priority 2: Google
    if google_key:
        # If user explicitly sets gemini-1.5-flash, litellm requires 'gemini/' prefix
        model = os.environ.get("MODEL_NAME", "gemini-1.5-pro-latest")
        if not model.startswith("gemini/"):
            model = f"gemini/{model}"
        return model
    
    # Priority 3: Claude
    if anthropic_key:
        model = os.environ.get("CLAUDE_MODEL_NAME", DEFAULT_CLAUDE_MODEL)
        # LiteLLM accepts bare claude names
        return model
        
    # Priority 4: Local Ollama
    local_model = os.environ.get("LOCAL_MODEL_NAME", DEFAULT_LOCAL_MODEL)
    if not local_model.startswith("ollama/"):
        local_model = f"ollama/{local_model}"
    return local_model

def get_chat_session(model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
    """
    Returns the unified LiteLLM Chat Session.
    """
    config_model = resolve_model_config()
    print(f"🧠 Booting Unified LiteLLM Session ({config_model})")
    return ChatSession(config_model, history, tools, system_instruction)
