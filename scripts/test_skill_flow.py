import os
import shutil
import sys
sys.path.append(os.path.join(os.getcwd(), "src"))
import dm_utils
import common_tools

# Setup Mock Campaign for Skill Test
def setup_mock_campaign():
    root = os.path.join(os.getcwd(), "campaigns", "skill_test")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    
    # Create current_session.txt pointing to session_1
    with open(os.path.join(root, "current_session.txt"), "w") as f:
        f.write("session_1")
        
    # Create Session 1 (Active)
    s1 = os.path.join(root, "session_1")
    os.makedirs(s1, exist_ok=True)
    
    # Simulate some initial log content
    with open(os.path.join(s1, "session_log.md"), "w") as f:
        f.write("# Session Log: session_1\n\n## Previously on...\nThe party defeated the goblins.\n")
        
    return root

def main():
    print("🧪 Setting up Mock Campaign for Skill Test...")
    root = setup_mock_campaign()
    
    # Force context to this campaign
    os.environ["DM_CAMPAIGN_ROOT"] = root
    
    # --- PHASE 1: PREPARATION ---
    print("\n[Phase 1] Checking Current State...")
    sessions = common_tools.list_sessions()
    print(f"Sessions: {sessions}")
    assert "session_1" in sessions, "Failed to list session_1"
    
    # --- PHASE 3: PLAY (Simulate logging) ---
    print("\n[Phase 3] Simulating Gameplay...")
    common_tools.log_event("The party enters the skill dungeon.")
    common_tools.log_event("They find a chest.", is_secret=True)
    
    log_content = common_tools.read_campaign_log("session")
    print(f"Log Content:\n{log_content}")
    assert "skill dungeon" in log_content, "Failed to log event"
    
    # --- PHASE 4: WRAP UP ---
    print("\n[Phase 4] Ending Session...")
    # Using manual summary to avoid API key requirement for test
    result = common_tools.end_session_and_compact(manual_summary="The party explored the skill dungeon and found a chest.")
    print(f"Wrap Up Result: {result}")
    
    # Verify Archive
    s1_dir = os.path.join(root, "session_1")
    archive_path = os.path.join(s1_dir, "session_log_full_archive.md")
    assert os.path.exists(archive_path), "Full archive not created"
    
    # Verify Summary in main log
    with open(os.path.join(s1_dir, "session_log.md"), "r") as f:
        summary_content = f.read()
    assert "The party explored the skill dungeon" in summary_content, "Summary not written to main log"
    
    # --- START NEXT SESSION ---
    print("\n[Next Session] Starting Session 2...")
    start_res = common_tools.start_new_session("Recap of session 1: The party found a chest.")
    print(f"Start Result: {start_res}")
    
    # Verify new session created
    s2_dir = os.path.join(root, "session_2")
    assert os.path.exists(s2_dir), "Session 2 folder not created"
    
    print("\n✅ Skill Workflow Verified Successfully!")
    
    # Cleanup
    # shutil.rmtree(root)

if __name__ == "__main__":
    main()
