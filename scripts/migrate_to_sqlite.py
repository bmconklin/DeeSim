import os
import sys
import json
import sqlite3

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.campaign import set_active_campaign, get_campaign_root
from core.database import init_db, get_db_connection
from core.players import register_player

def migrate_campaign(campaign_name: str):
    print(f"--- Migrating Campaign: {campaign_name} ---")
    set_active_campaign(campaign_name)
    root = get_campaign_root()
    
    if not os.path.exists(root):
        print(f"Campaign {campaign_name} not found.")
        return
        
    # Initialize DB tables
    init_db()
    
    with get_db_connection() as conn:
        
        # 1. Migrate Players
        players_file = os.path.join(root, "player_mapping.json")
        if os.path.exists(players_file):
            print("Migrating players...")
            with open(players_file, "r") as f:
                players = json.load(f)
                for slack_id, name in players.items():
                    # We use the actual function to ensure standard registration
                    register_player(slack_id, name)
            
            # Optional: Rename the old file so it's not read again
            os.rename(players_file, players_file + ".bak")
            
        # 2. Migrate Quests
        quests_file = os.path.join(root, "quests.json")
        if os.path.exists(quests_file):
            print("Migrating quests...")
            with open(quests_file, "r") as f:
                quests = json.load(f)
                for title, data in quests.items():
                    desc = data.get("description", "")
                    status = data.get("status", "Active")
                    
                    cursor = conn.execute("SELECT id FROM quests WHERE title = ?", (title,))
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO quests (title, description, status) VALUES (?, ?, ?)",
                            (title, desc, status)
                        )
            os.rename(quests_file, quests_file + ".bak")
            
        # 3. Migrate Inventories
        for filename in os.listdir(root):
            if filename.startswith("inventory_") and filename.endswith(".json"):
                print(f"Migrating {filename}...")
                character_name_safe = filename[10:-5]
                # Reconstruct a best-guess character name or use what we know
                # In our new system inventory uses slack_id. 
                # Let's find the slack ID for this character.
                char_name = character_name_safe.replace("_", " ").title()
                
                cursor = conn.execute("SELECT slack_id FROM players WHERE character_name LIKE ?", (f"%{char_name}%",))
                row = cursor.fetchone()
                if row:
                    slack_id = row['slack_id']
                else:
                    # Create a dummy NPC record for orphaned inventories
                    import uuid
                    slack_id = f"npc_{str(uuid.uuid4())[:8]}"
                    conn.execute("INSERT INTO players (slack_id, character_name) VALUES (?, ?)", (slack_id, char_name))
                
                with open(os.path.join(root, filename), "r") as f:
                    inv_data = json.load(f)
                    
                for item_name, details in inv_data.items():
                    qty = details.get("quantity", 1)
                    wt = details.get("weight", 0.0)
                    
                    # Avoid duplicates if script run twice
                    cursor = conn.execute("SELECT quantity FROM inventory WHERE character_id = ? AND item_name = ?", (slack_id, item_name))
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO inventory (character_id, item_name, quantity, weight) VALUES (?, ?, ?, ?)",
                            (slack_id, item_name, qty, wt)
                        )
                
                os.rename(os.path.join(root, filename), os.path.join(root, filename + ".bak"))
                
    print("Migration Complete!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate old JSON state to SQLite.")
    parser.add_argument("campaign", help="Name of the campaign to migrate (e.g., 'local')")
    args = parser.parse_args()
    
    migrate_campaign(args.campaign)
