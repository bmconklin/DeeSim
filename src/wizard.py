import os
import json
import shutil
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("==========================================")
    print("      AGENTIC DUNGEON MASTER SETUP        ")
    print("==========================================\n")

def get_input(prompt, default=None):
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input.strip() else default
    return input(f"{prompt}: ")

def create_campaign():
    print_header()
    campaign_name = get_input("Enter Campaign Name", "New Adventure")
    base_name = campaign_name.lower().replace(" ", "_")
    
    # Path setup
    current_dir = os.getcwd()
    campaign_dir = os.path.join(current_dir, "campaigns", base_name)
    
    if os.path.exists(campaign_dir):
        print(f"\nWarning: Campaign folder '{base_name}' already exists.")
        overwrite = get_input("Overwrite?", "n")
        if overwrite.lower() != 'y':
            print("Aborting setup.")
            sys.exit(0)
    
    os.makedirs(campaign_dir, exist_ok=True)
    
    # Create World Info file (Persistent Context)
    with open(os.path.join(campaign_dir, "world_info.md"), "w") as f:
        f.write(f"# World Info: {campaign_name}\n\n## Important Locations\n\n## Important NPCs\n")

    # Create Session 1
    session_dir = os.path.join(campaign_dir, "session_1")
    os.makedirs(session_dir, exist_ok=True)
    
    # Track current session
    with open(os.path.join(campaign_dir, "current_session.txt"), "w") as f:
        f.write("session_1")
    
    # Create initial log files in session_1
    with open(os.path.join(session_dir, "session_log.md"), "w") as f:
        f.write(f"# Session Log: {campaign_name} - Session 1\n\n")
        
    with open(os.path.join(session_dir, "secrets_log.md"), "w") as f:
        f.write(f"# DM Secrets: {campaign_name} - Session 1\n\n")
        
    return campaign_name, campaign_dir

def generate_client_config(server_script_path):
    print("\n--- Client Configuration ---")
    print("Select your AI Client:")
    print("1) Claude Desktop")
    print("2) Claude CLI")
    print("3) Gemini / Other MCP Client")
    
    choice = get_input("Selection", "1")
    
    python_path = sys.executable
    
    config_data = {
        "mcpServers": {
            "dungeon-master": {
                "command": python_path,
                "args": [server_script_path]
            }
        }
    }
    
    config_json = json.dumps(config_data, indent=2)
    
    if choice == "1":
        filename = "claude_desktop_config.json"
        print(f"\nGeneratinig {filename}...")
        with open(filename, "w") as f:
            f.write(config_json)
            
        print(f"\n[ACTION REQUIRED] To enable the DM tools in Claude Desktop:")
        print(f"Run this command to copy the config (MacOS/Linux):")
        print(f"cp {filename} ~/Library/Application\\ Support/Claude/claude_desktop_config.json")
        print("(Note: If you already have a config there, you should manually merge the contents.)")
        
    elif choice == "2":
        print("\nFor Claude CLI, you typically pass the config via a flag or env var.")
        print("Generated 'mcp_config.json' for your reference.")
        with open("mcp_config.json", "w") as f:
            f.write(config_json)
            
    else:
        print("\nGenerated generic 'mcp_config.json'. Configure your client to run the python script as the server.")
        with open("mcp_config.json", "w") as f:
            f.write(config_json)

def main():
    clear_screen()
    campaign_name, campaign_dir = create_campaign()
    
    print(f"\nCampaign '{campaign_name}' initialized at:")
    print(f"{campaign_dir}")
    
    # Generate System Prompt
    system_prompt = f"""
You are the Dungeon Master for the campaign '{campaign_name}'.
Your Goal: Run a fair, engaging, and rules-accurate D&D 5e game.

CORE RULE: DO NOT Hallucinate dice rolls or rules.
- DICE ROLLING:
  - Ask the player at the start: "Do you prefer to roll your own physical dice, or should I roll for you?"
  - IF PLAYER ROLLS (Manual):
      1. FIRST, determine the DC and Failure Consequence.
      2. CALL `request_player_roll(check_type, dc, consequence)` to log this commitment TO YOURSELF.
      3. ONLY THEN, ask the player to roll.
      4. Trust their reported result and use `log_event` to record it.
  - IF DM ROLLS (Auto):
      - ALWAYS use the `roll_dice` tool.
      - NEVER use `request_player_roll` if you are rolling for them.
- ALWAYS use the `roll_dice` tool for NPC/Monster checks.
  - Always document the intent of the roll and possible consequences in the campaign's secrets log BEFORE asking for the roll.
  - After the roll, reference the secrets log before deciding how to respond to players.
- ALWAYS use the `lookup_rule` tool if you are unsure of a specific mechanic.
  - When answering questions about rules, always use the `lookup_rule` tool first.
  - If the answer is not found, try to think of a fair way to handle the situation based on the spirit of the game.
  - When explaining a rule or mechanic, always cite your source with the relevant book, page, and section.
- Log important story beats to `log_event`.
  - When it feels like a natural transition to a new story arc, or a significant event has occurred, ask if we should start a new log to prevent having too much in one log.

SESSION MANAGEMENT:
- The campaign is divided into sessions.
- Use `start_new_session(summary)` when the player agrees to end the current session.
- Use `start_new_session(summary)` when the player agrees to end the current session.
- PERSISTENT FACTS are stored in `world_info.md`. You should update this file (via users request or manual edit guidance) for major details like NPC names or locations that must stay consistent.
- MEMORY RETRIEVAL: You have a tool `read_campaign_log(log_type)`.
  - Use this if you need to recall details from previous sessions ('session'), secret DM notes ('secrets'), or world facts ('world').
  - If a user asks "What happened last time?", call `read_campaign_log('session')` first.

DEBUG MODE:
- You have a tool `set_debug_mode(True/False)`.
- If the user asks for "Debug Mode", "Verbose Mode", or "Show your work", call `set_debug_mode(True)`.
- When Debug Mode is ENABLED:
    - The tools (`roll_dice`, `lookup_rule`) will return detailed system info (log paths, source text, exact modifiers).
    - You must explicitly explain your reasoning to the player, citing the rules and showing the math.
- If the user asks for "Story Mode" or to hide details, call `set_debug_mode(False)`.

DIALOGUE & NARRATIVE Control:
- You MUST speak, act, and think for all NPCs, Monsters, and the Environment.
- You MUST NOT speak, act, or decide the thoughts of the Player Characters (PCs).
- When an NPC speaks, write their dialogue out fully.
- Do not narrate the PC's reaction to an event (e.g. "Grog looks scared"). Let the player tell you how they react.

FALLBACK PROTOCOLS (When Tools Fail):
- If `validate_action` returns "Skipped/Disabled":
    - Use your own knowledge of D&D 5e to check the move.
    - Be permissive. If it seems roughly correct, allow it.
    - Warn the player: "My rulebook is offline, but I'll allow this based on my memory."
- If `generate_name` returns "Custom names require GOOGLE_API_KEY":
    - IGNORE the error.
    - INVENT a creative name yourself instantly. Do not complain to the user.
- If `summarize_session` or `propose_image` are disabled:
    - Simply proceed without them. Provide a text summary in chat if asked.
    - Describe scenes vividly in text instead of generating images.

CURRENT CAMPAIGN DIRECTORY: {campaign_dir}
    """
    
    prompt_path = os.path.join(campaign_dir, "system_prompt.txt")
    with open(prompt_path, "w") as f:
        f.write(system_prompt)
        
    print(f"\nGenerated 'system_prompt.txt' in {campaign_dir}. Copy this into your AI Agent's system prompt instructions.")
    
    # Config setup
    abs_server_path = os.path.abspath("src/mcp_server.py")
    generate_client_config(abs_server_path)
    
    print("\n\nsetup complete! You are ready to verify configuration and start playing.")

if __name__ == "__main__":
    main()
