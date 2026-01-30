
import os
import sys
import json
import shutil
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath("src"))

import dm_utils
from core.engine import GameEngine

def setup_test_campaign(name, text):
    root = os.path.join("campaigns", name)
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "current_session.txt"), "w") as f:
        f.write("session_1")
    session_dir = os.path.join(root, "session_1")
    os.makedirs(session_dir, exist_ok=True)
    with open(os.path.join(session_dir, "chat_history.json"), "w") as f:
        json.dump([{"role": "assistant", "parts": [text]}], f)
    return root

def test_multi_campaign():
    print("🧪 Testing Multi-Campaign Isolation...")
    
    # 1. Setup two test campaigns
    try:
        setup_test_campaign("test_alpha", "This is the Alpha campaign.")
        setup_test_campaign("test_beta", "This is the Beta campaign.")
        
        # 2. Bind channels
        dm_utils.bind_channel_to_campaign("slack", "C111", "test_alpha")
        dm_utils.bind_channel_to_campaign("slack", "C222", "test_beta")
        
        # 3. Initialize Engine (with mocked LLM bridge to avoid API calls)
        with patch("llm_bridge.get_chat_session") as mock_get_session:
            # Mock session behavior
            mock_session_alpha = MagicMock()
            mock_session_beta = MagicMock()
            
            def side_effect(model_name, history, tools, system_instruction):
                if "Alpha" in str(history):
                    return mock_session_alpha
                return mock_session_beta
                
            mock_get_session.side_effect = side_effect
            
            engine = GameEngine(tools_list=[])
            
            # 4. Simulate message from Channel 1 (Alpha)
            mock_session_alpha.send_message.return_value.text = "Alpha response"
            res1 = engine.process_message("U1", "User1", "Hello", "slack", channel_id="C111")
            print(f"Channel C111 Response: {res1}")
            
            # 5. Simulate message from Channel 2 (Beta)
            mock_session_beta.send_message.return_value.text = "Beta response"
            res2 = engine.process_message("U2", "User2", "Hello", "slack", channel_id="C222")
            print(f"Channel C222 Response: {res2}")
            
            # 6. Verify Context
            assert "test_alpha" in str(engine.sessions.keys())
            assert "test_beta" in str(engine.sessions.keys())
            print("✅ Sessions isolated successfully.")
            
    finally:
        # Cleanup
        if os.path.exists("campaigns/test_alpha"):
            shutil.rmtree("campaigns/test_alpha")
        if os.path.exists("campaigns/test_beta"):
            shutil.rmtree("campaigns/test_beta")

if __name__ == "__main__":
    test_multi_campaign()
