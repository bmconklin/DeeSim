import os
import sys
import json
from dotenv import load_dotenv

# Load Env
load_dotenv()

from bot import tools_list, get_chat_session, DEBUG_MODE
import dm_utils

# Colors
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
NC = '\033[0m'

def print_banner():
    print(f"{GREEN}")
    print("==========================================")
    print("      AGENTIC DM - TERMINAL CLIENT        ")
    print("==========================================")
    print(f"{NC}")
    print("Type your action or dialogue.")
    print("Commands: /quit, /debug, /roll <dice>")
    print("------------------------------------------\n")

def main():
    print_banner()
    
    # 1. Load Campaign Check
    campaign_root = os.environ.get("DM_CAMPAIGN_ROOT")
    if not campaign_root or not os.path.exists(campaign_root):
        print(f"{RED}Error: DM_CAMPAIGN_ROOT invalid.{NC}")
        print("Please set it in .env or run setup_slack.sh first.")
        return

    print(f"{BLUE}Playing Campaign: {os.path.basename(campaign_root)}{NC}")
    
    # 2. Load System Prompt
    prompt_path = os.path.join(campaign_root, "system_prompt.txt")
    if not os.path.exists(prompt_path):
        print(f"{RED}Error: system_prompt.txt not found.{NC}")
        return
        
    with open(prompt_path, "r") as f:
        system_instruction = f.read()
        
    # 3. Load History
    history = dm_utils.load_chat_snapshot()
    if not history:
        print("✨ Starting fresh session logic...")
    else:
        print(f"✨ Resumed session ({len(history)} messages).")
        
    # 4. Initialize Session
    model_name = os.environ.get("MODEL_NAME", "gemini-1.5-pro-latest")
    
    try:
        session = get_chat_session(model_name, history, tools_list, system_instruction)
    except Exception as e:
        print(f"{RED}Failed to initialize AI: {e}{NC}")
        return

    # 5. Game Loop
    while True:
        try:
            user_input = input(f"{YELLOW}You > {NC}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
            
        if not user_input.strip():
            continue
            
        if user_input.lower() in ["/quit", "/exit"]:
            print("Goodbye!")
            break
            
        if user_input.startswith("/roll "):
            # Client-side roll helper
            expr = user_input.replace("/roll ", "")
            res = dm_utils.roll_dice(expr)
            if "error" in res:
                print(f"{RED}{res['error']}{NC}")
            else:
                print(f"🎲 Rolled {res['total']} ({res['rolls']} {res['modifier']})")
                # We don't send this to bot unless user types it
            continue

        # Send to AI
        print("...")
        try:
            response = session.send_message([user_input])
            
            # Extract text
            ai_text = ""
            # Handle different backend response types (Gemini vs Claude vs Local)
            # Our bridge tries to normalize, but let's be safe.
            if hasattr(response, "text"):
                ai_text = response.text
            elif isinstance(response, dict) and "text" in response:
                ai_text = response["text"]
            else:
                ai_text = str(response)
                
            print(f"{GREEN}DM > {ai_text}{NC}\n")
            
            # Save History (The session object updates its internal history, we need to persist it)
            # The bridge doesn't auto-save to disk, bot.py does. We must do it here.
            # We need to get the UPDATED history from the session.
            new_history = session.get_history()
            dm_utils.save_chat_snapshot(new_history)
            
        except Exception as e:
            print(f"{RED}Error: {e}{NC}")

if __name__ == "__main__":
    main()
