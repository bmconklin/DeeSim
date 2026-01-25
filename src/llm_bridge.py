import os
import json
import requests
from typing import List, Dict, Any, Optional

# Constants
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/chat"
DEFAULT_LOCAL_MODEL = "llama3"

class LocalChatSession:
    """
    A compatible wrapper for Ollama/Local LLM that mimics google.genai.chats.Chat
    """
    def __init__(self, model: str, history: List[Dict], system_instruction: str, tools: List[Any]):
        self.model = model
        self.history = history if history else [] # Format: [{"role": "user", "parts": ["text"]}, ...]
        self.system_instruction = system_instruction
        self.tools = tools # We might need to serialize these for Ollama if it supports tools
        self.api_url = os.environ.get("OLLAMA_HOST", OLLAMA_DEFAULT_URL)
        
        # Normalize history to Ollama format if needed (Google uses 'parts', Ollama uses 'content')
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

    def send_message(self, content_parts: List[Any]) -> Any:
        """
        Sends a message to the local LLM and returns a compat response object.
        """
        # 1. Parse Input
        user_text = ""
        for part in content_parts:
            # Handle Text
            if isinstance(part, str):
                user_text += part + "\n"
            # Handle Images (Ollama supports images in some endpoints, but let's stick to text for now)
            # If we pass an object with .to_bytes, skip it or describe it?
            # For simplicity in V1 Local, we might skip actual image bytes
            
        self.context_window.append({"role": "user", "content": user_text})
        
        # 2. Call API
        payload = {
            "model": self.model,
            "messages": self.context_window,
            "stream": False
        }
        
        try:
            print(f"📡 Sending to Local LLM ({self.api_url})...")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            ai_text = data.get("message", {}).get("content", "")
            
            # 3. Update History
            self.context_window.append({"role": "assistant", "content": ai_text})
            # Also update the 'Gemini-style' history for persistence
            self.history.append({"role": "user", "parts": [user_text]})
            self.history.append({"role": "model", "parts": [ai_text]})
            
            # 4. Return compatible response object
            class MockResponse:
                def __init__(self, text):
                    self.text = text
            
            return MockResponse(ai_text)
            
        except Exception as e:
            return MockResponse(f"Local LLM Error: {e}")

    def get_history(self):
        return self.history


def get_chat_session(model_name: str, history: List[Dict], tools: List[Any], system_instruction: str):
    """
    Factory to return either a Google Chat or a Local Chat.
    """
    google_key = os.environ.get("GOOGLE_API_KEY")
    
    if google_key:
        # Use Google GenAI
        import google.genai as genai
        from google.genai import types
        
        client = genai.Client(api_key=google_key)
        return client.chats.create(
            model=model_name,
            history=history,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
    else:
        # Use Local LLM
        local_model = os.environ.get("LOCAL_MODEL_NAME", DEFAULT_LOCAL_MODEL)
        print(f"🔌 GOOGLE_API_KEY not found. Switching to Local LLM: {local_model}")
        return LocalChatSession(local_model, history, system_instruction, tools)
