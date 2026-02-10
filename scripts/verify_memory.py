import os
import shutil
import sys
sys.path.append(os.path.join(os.getcwd(), "src"))
import dm_utils
import common_tools

# Setup Mock Data
def setup_mock_campaign():
    root = os.path.join(os.getcwd(), "campaigns", "test_memory")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    
    # Create Session 1 (Mentioning Goblin King)
    s1 = os.path.join(root, "session_1")
    os.makedirs(s1, exist_ok=True)
    with open(os.path.join(s1, "session_log.md"), "w") as f:
        f.write("# Session 1 Summary\nThe party met the Goblin King in the dark cave.")
    with open(os.path.join(s1, "chat_history.json"), "w") as f:
        f.write('[{"role": "user", "parts": ["Hello Goblin King"]}]')

    # Create Session 2 (Different topic)
    s2 = os.path.join(root, "session_2")
    os.makedirs(s2, exist_ok=True)
    with open(os.path.join(s2, "session_log.md"), "w") as f:
        f.write("# Session 2 Summary\nThe party flew to the moon.")
        
    return root

def main():
    print("🧪 Setting up Mock Campaign...")
    root = setup_mock_campaign()
    
    # Force context to this campaign
    os.environ["DM_CAMPAIGN_ROOT"] = root
    
    print("\n🔎 Test 1: Search Summaries (Query: 'Goblin')")
    result = common_tools.lookup_past_session(query="Goblin")
    print(f"Result:\n{result}")
    
    assert "session_1" in result, "Failed to find session_1"
    assert "Goblin King" in result, "Failed to find content snippet"
    
    print("\n🔎 Test 2: Read History (Session: 'session_1')")
    result_hist = common_tools.lookup_past_session(query="IGNORED", session_name="session_1")
    print(f"Result:\n{result_hist}")
    
    assert "Hello Goblin King" in result_hist or "# Session 1 Summary" in result_hist, "Failed to read history"
    
    print("\n✅ Verification Successful!")
    
    # Cleanup
    # shutil.rmtree(root)

if __name__ == "__main__":
    main()
