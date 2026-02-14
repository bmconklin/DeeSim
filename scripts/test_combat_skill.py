import os
import shutil
import sys
import json
sys.path.append(os.path.join(os.getcwd(), "src"))
import dm_utils
import common_tools

# Setup Mock Campaign for Skill Test
def setup_mock_campaign():
    root = os.path.join(os.getcwd(), "campaigns", "combat_skill_test")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    
    # Create current_session.txt pointing to session_1
    with open(os.path.join(root, "current_session.txt"), "w") as f:
        f.write("session_1")
        
    s1 = os.path.join(root, "session_1")
    os.makedirs(s1, exist_ok=True)
    return root

def main():
    print("🧪 verification: Setting up Mock Campaign for Combat Skill Test...")
    root = setup_mock_campaign()
    
    # Force context to this campaign
    os.environ["DM_CAMPAIGN_ROOT"] = root
    
    # --- PHASE 1: INITIATION ---
    print("\n[Phase 1] Initializing Combat...")
    entities = [
        {"name": "Goblin 1", "hp": 7, "max_hp": 7, "ac": 15},
        {"name": "Goblin 2", "hp": 7, "max_hp": 7, "ac": 15}
    ]
    # Simulate calling initialize_combat via MCP (passing JSON string)
    initial_log = common_tools.initialize_combat(entities) # common_tools expects list, mcp expects string. Testing common_tools.
    print(f"Init Log: {initial_log}")
    
    state = dm_utils.get_combat_state()
    assert "Goblin 1" in state, "Goblin 1 not found in state"
    assert "7/7" in state, "HP incorrect"
    
    # --- PHASE 2: COMBAT LOOP (Simulate Damage) ---
    print("\n[Phase 2] Simulating Damage (Player hits Goblin 1)...")
    # Simulate: Player hits Goblin 1 for 4 damage
    update_res = common_tools.track_combat_change("Goblin 1", -4, "Bloody")
    print(f"Update Result:\n{update_res}")
    
    state_after_hit = dm_utils.get_combat_state()
    # Check if Goblin 1 has 3 HP (7 - 4)
    # The output format is markdown table, so we need to parse or grep
    # Assuming "Goblin 1 | 3/7" or similar
    assert "Goblin 1" in state_after_hit
    # Simple check for the number 3
    # A robust check would parse the line for Goblin 1
    hit_line = [line for line in state_after_hit.split('\n') if "Goblin 1" in line][0]
    print(f"Goblin 1 Line: {hit_line}")
    assert "3/7" in hit_line or "3 / 7" in hit_line, "HP did not update correctly to 3/7"
    assert "Bloody" in hit_line, "Notes did not update"
    
    # --- PHASE 3: TERMINATION ---
    print("\n[Phase 3] Ending Combat...")
    common_tools.log_event("Combat ended. Victory for the party.")
    
    # Cleanup (Optional)
    # shutil.rmtree(root)
    
    print("\n✅ Combat Skill Workflow Verified Successfully!")

if __name__ == "__main__":
    main()
