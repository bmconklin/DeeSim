import sys
import os
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from llm_bridge import get_chat_session, LocalChatSession, GoogleChatSession, ClaudeChatSession

def test_session():
    print("Testing Session Factory...")
    try:
        session = get_chat_session("test-model", [], [], "System Prompt")
        print(f"Session Type: {type(session).__name__}")
        
        if isinstance(session, LocalChatSession):
            print(f"✅ Local Mode Active. Model: {session.model}")
            print(f"   API URL: {session.api_url}")
        elif isinstance(session, GoogleChatSession):
            print(f"⚠️ Google Mode Active.")
        elif isinstance(session, ClaudeChatSession):
            print(f"⚠️ Claude Mode Active.")
        else:
            print(f"❓ Unknown Session Type.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_session()
