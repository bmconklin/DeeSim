import json
import logging
import requests
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))

from common_tools import roll_dice
from llm_bridge import LocalChatSession

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_ollama():
    print("🧪 Testing Ollama Payload Construction...")
    
    # 1. Setup Session
    model = "llama3"
    tools = [roll_dice]
    history = []
    system_prompt = "You are a test bot."
    
    session = LocalChatSession(model, history, system_prompt, tools)
    
    # 2. Trigger payload construction logic manually (by inspecting internals or mocking requests)
    # We will subclass/mock requests to capture the payload
    
    payload = {
        "model": session.model,
        "messages": session.context_window + [{"role": "user", "content": "Hello"}],
        "stream": False,
        "tools": session.ollama_tools
    }
    
    print("\n📦 Generated Payload:")
    print(json.dumps(payload, indent=2))
    
    # 3. Try sending it for real
    print(f"\n📡 Sending to {session.api_url}...")
    try:
        response = requests.post(session.api_url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_ollama()
