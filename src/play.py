import os
import sys
import json

# Suppress harmless ONNX C++ and tokenizer warnings for Apple Silicon
os.environ["ONNXRUNTIME_LOG_LEVEL"] = "3"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv

# Load Env
load_dotenv()

# --- CAMPAIGN SELECTION ---
# If DM_ACTIVE_CAMPAIGN is set (from play.sh), dm_utils will pick it up automatically.
# We no longer need manual path resolution here unless the user passed a direct path via sys.argv.
if len(sys.argv) > 1:
    arg = sys.argv[1]
    if os.path.exists(arg) and os.path.isabs(arg):
        os.environ["DM_CAMPAIGN_ROOT"] = arg
        print(f"🎯 CLI Override: Explicit path '{arg}'")
    else:
        os.environ["DM_ACTIVE_CAMPAIGN"] = arg
        print(f"🎯 CLI Pivot: Campaign name '{arg}'")

# from bot import tools_list, DEBUG_MODE # Removed to avoid Slack dependency
from llm_bridge import get_chat_session, resolve_model_config
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
    common_tools.generate_name,
    common_tools.initialize_combat,
    common_tools.track_combat_change
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
    campaign_root = dm_utils.get_campaign_root()
    if not os.path.exists(campaign_root):
        os.makedirs(campaign_root, exist_ok=True)

    print(f"{BLUE}Playing Campaign: {os.path.basename(campaign_root)}{NC}")
    
    # 2. Load System Prompt
    system_instruction = dm_utils.get_system_instruction()
        
    # 3. Load History
    history = dm_utils.load_chat_snapshot()
    if not history:
        print("✨ Starting fresh session logic...")
    else:
        print(f"✨ Resumed session ({len(history)} messages).")
        
    # 4. Initialize Session
    # Try to determine if Google is active so we can warn about images
    model_name = resolve_model_config()
    provider = "google" if "gemini" in model_name else "local"
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
    def _submit(event):
        """Submit when Enter is pressed."""
        event.current_buffer.validate_and_handle()

    @kb.add('escape', 'enter')
    def _newline(event):
        """Insert newline when Esc+Enter (Alt+Enter) is pressed."""
        event.current_buffer.insert_text('\n')
        
    # Attempt Shift+Enter (May not work in all terminals)
    # prompt_toolkit often sees Shift+Enter as just Enter
    
    @kb.add('c-d')
    def _exit(event):
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
            ai_text = getattr(response, "text", None)
            if ai_text is None and isinstance(response, dict):
                ai_text = response.get("text")  # pylint: disable=no-member
            
            # Fallback if text is still None (e.g. Safety Block)
            if not ai_text:
                ai_text = "[System: The DM is silent. (No response text returned. This usually indicates a Safety Block or an internal model error.)]"
            
            print(f"{GREEN}DM > {ai_text}{NC}\n")
            
            # Save History (The session object updates its internal history, we need to persist it)
            new_history = session.get_history()
            dm_utils.save_chat_snapshot(new_history)
            
            # --- Auto-Image Generation ---
            # 1. Check for regex-scraped prompt
            image_found = dm_utils.extract_and_save_prompt_from_text(ai_text)
            
            # 2. Trigger generation if prompt exists (either from tool or regex)
            image_path, _ = dm_utils.generate_image_from_pending()
            if image_path:
                if image_path == "SUCCESS_BUT_SAVE_FAILED":
                    print(f"{YELLOW}🖼️ Image generated but failed to save to campaign folder.{NC}")
                else:
                    print(f"{BLUE}🖼️ Image saved to: {image_path}{NC}\n")
            
        except Exception as e:
            print(f"{RED}Error: {e}{NC}")

if __name__ == "__main__":
    main()
