import os
import sys
import json
from dotenv import load_dotenv

# Load Env
# Load Env
load_dotenv()

# --- CAMPAIGN SELECTION (Before Imports) ---
if len(sys.argv) > 1:
    arg_campaign = sys.argv[1]
    # Check if absolute path or name
    if os.path.isabs(arg_campaign):
        target_path = arg_campaign
    else:
        # Assume it's in the 'campaigns' folder
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_path = os.path.join(root_dir, "campaigns", arg_campaign)
        
    if os.path.exists(target_path):
        os.environ["DM_CAMPAIGN_ROOT"] = target_path
        print(f"🎯 CLI Override: Loading campaign from '{target_path}'")
    else:
        print(f"⚠️ Warning: Campaign '{arg_campaign}' not found at {target_path}. Using default from .env")

# from bot import tools_list, DEBUG_MODE # Removed to avoid Slack dependency
from llm_bridge import get_chat_session
import dm_utils
import common_tools

# --- Local Tool Overrides ---
def send_dm(character_name: str, message: str) -> str:
    """
    Sends a PRIVATE Direct Message to a specific player.
    (Local Mode: Prints to console effectively, or logs to secrets).
    """
    print(f"\n[PRIVATE MESSAGE to {character_name}]: {message}\n")
    return f"Sent private message to {character_name}."

# Construct Tools List
tools_list = [
    common_tools.roll_dice, 
    common_tools.log_event, 
    common_tools.lookup_rule, 
    common_tools.search_dnd_rules, 
    common_tools.verify_dnd_statement, 
    common_tools.find_monster_by_cr, 
    common_tools.start_new_session, 
    common_tools.request_player_roll, 
    common_tools.read_campaign_log,
    send_dm, # LOCAL VERSION
    common_tools.end_session_and_compact,
    common_tools.update_world_info,
    common_tools.propose_scene_image,
    common_tools.validate_action,
    common_tools.complete_setup_step,
    common_tools.submit_character_sheet,
    common_tools.generate_name
]

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
    provider, model_name = llm_bridge.resolve_model_config()
    print(f"🚀 Starting session with {provider} model: {model_name}")
    
    try:
        session = get_chat_session(model_name, history, tools_list, system_instruction)
    except Exception as e:
        print(f"{RED}Failed to initialize AI: {e}{NC}")
        return

    # 5. Game Loop
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    
    # Configure Keybindings
    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        """Submit when Enter is pressed."""
        event.current_buffer.validate_and_handle()

    @kb.add('escape', 'enter')
    def _(event):
        """Insert newline when Esc+Enter (Alt+Enter) is pressed."""
        event.current_buffer.insert_text('\n')
        
    # Attempt Shift+Enter (May not work in all terminals)
    # prompt_toolkit often sees Shift+Enter as just Enter
    
    @kb.add('c-d')
    def _(event):
        """Exit when Ctrl-D is pressed."""
        print("\nExiting...")
        sys.exit(0)

    prompt_session = PromptSession(key_bindings=kb)

    print(f"{YELLOW}Input Mode: Multiline enabled.{NC}")
    print(f"{YELLOW} - Press [Enter] to SUBMIT.{NC}")
    print(f"{YELLOW} - Press [Alt+Enter] (or Esc+Enter) for new line.{NC}")
    
    while True:
        try:
            # Replaces standard input()
            user_input = prompt_session.prompt(f"You > ", multiline=True)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
            
        if not user_input.strip():
            continue
            
        if user_input.lower().strip() in ["/quit", "/exit"]:
            print("Goodbye!")
            break
            
        if user_input.strip().startswith("/roll "):
            # Client-side roll helper
            expr = user_input.strip().replace("/roll ", "")
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
            # Handle different backend response types (Gemini vs Claude vs Local)
            ai_text = None
            if hasattr(response, "text"):
                ai_text = response.text
            elif isinstance(response, dict):
                ai_text = response.get("text")
            
            # Fallback if text is still None (e.g. Safety Block)
            if not ai_text:
                ai_text = "[System: The DM is silent. (No response text returned. This usually indicates a Safety Block or an internal model error.)]"
            
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
