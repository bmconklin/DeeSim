from mcp.server.fastmcp import FastMCP
import dm_utils
import dnd_bridge
import os

# Initialize FastMCP Server
mcp = FastMCP("DungeonMasterTools")

# campaigning paths are handled by dm_utils
from dm_utils import get_campaign_root, get_current_session_dir, get_log_paths

# Note: dm_utils tools now handle missing API keys gracefully.
# No extra logic needed here as we delegate to them.


@mcp.tool()
def start_new_session(summary_of_previous: str) -> str:
    """
    Archives the current session and starts a new one.
    Args:
        summary_of_previous: A brief summary of what happened in the last session to seed the next log.
    """
    # 1. Determine next session number
    root = get_campaign_root()
    current_session_file = os.path.join(root, "current_session.txt")
    if not os.path.exists(current_session_file):
        return "Error: Could not find current_session.txt. Is this a valid campaign?"
        
    with open(current_session_file, "r") as f:
        current_name = f.read().strip()
        
    # Assume format "session_N"
    try:
        current_num = int(current_name.split("_")[1])
    except:
        current_num = 0
        
    next_num = current_num + 1
    next_session_name = f"session_{next_num}"
    next_session_dir = os.path.join(get_campaign_root(), next_session_name)
    
    # 2. Create new directory
    os.makedirs(next_session_dir, exist_ok=True)
    
    # 3. Initialize logs
    with open(os.path.join(next_session_dir, "session_log.md"), "w") as f:
        f.write(f"# Session Log: {next_session_name}\n\n")
        f.write(f"## Previously on...\n{summary_of_previous}\n\n")
        
    with open(os.path.join(next_session_dir, "secrets_log.md"), "w") as f:
        f.write(f"# DM Secrets: {next_session_name}\n\n")
        
    # 4. Update pointer
    with open(current_session_file, "w") as f:
        f.write(next_session_name)
        
    return f"Successfully started {next_session_name}. Previous session archived."

# Global State
DEBUG_MODE = False

@mcp.tool()
def set_debug_mode(debug: bool) -> str:
    """
    Toggles Debug Mode.
    If True, dice rolls and rule lookups will return highly detailed system information (source, log files, etc.).
    If False, returns simple narrative-ready results.
    """
    global DEBUG_MODE
    DEBUG_MODE = debug
    state = "ENABLED" if debug else "DISABLED"
    return f"Debug Mode {state}. I will providing detailed source/log info for all actions if enabled."

@mcp.tool()
def request_player_roll(check_type: str, dc: int, consequence: str) -> str:
    """
    Call this BEFORE asking the player to roll.
    Logs the DC and Consequence to the secrets log so the DM cannot 'change their mind' after seeing the result.
    Args:
        check_type: What is being rolled? (e.g. "Stealth Check", "Strength Save")
        dc: The Difficulty Class (e.g. 15)
        consequence: What happens on failure? (e.g. "The guards spot you", "Half damage")
    """
    session_log, secrets_log = get_log_paths()
    
    log_message = f"**WAITING FOR PLAYER** | Type: {check_type} | DC: {dc} | Fail Consequence: {consequence}"
    dm_utils.log_to_file(secrets_log, log_message)
    
    response = "Logged DC and Consequence. You may now ask the player to roll."
    
    if DEBUG_MODE:
        return f"""[DEBUG_MODE]
Action: request_player_roll
Log File: {secrets_log}
Content: {log_message}
Output: {response}"""

    return response

@mcp.tool()
def roll_dice(expression: str, purpose: str, is_secret: bool = False) -> str:
    """
    Rolls dice and logs the result permanently.
    Args:
        expression: Dice string like '1d20+5'
        purpose: Why is this roll happening? (e.g. "Attack roll vs Goblin")
        is_secret: If True, result is hidden from players (logged to secrets file).
    """
    result = dm_utils.roll_dice(expression)
    
    if "error" in result:
        return result["error"]
        
    session_log, secrets_log = get_log_paths()
    
    log_file = secrets_log if is_secret else session_log
    log_type = "SECRET ROLL" if is_secret else "PUBLIC ROLL"
    
    log_message = f"**{log_type}** | Purpose: {purpose} | Result: {result['total']} ({result['rolls']} {result['modifier']})"
    dm_utils.log_to_file(log_file, log_message)
    
    base_response = f"Rolled {expression} for {purpose}. Result: {result['total']} (Details: {result['rolls']} + {result['modifier']})"
    
    if DEBUG_MODE:
        return f"""[DEBUG_MODE]
Action: roll_dice('{expression}')
Purpose: {purpose}
Secret: {is_secret}
Log File: {log_file}
Raw Result: {result}
Output: {base_response}"""

    return base_response

@mcp.tool()
def lookup_rule(query: str) -> str:
    """
    Searches the D&D 5e SRD rules for a specific term.
    Args:
        query: The rule topic to search for (e.g. "grapple", "rest", "cover")
    """
    return dnd_bridge.search_dnd_rules(query)

@mcp.tool()
def log_event(message: str, is_secret: bool = False) -> str:
    """
    Logs a narrative event or DM thought permanently.
    Args:
        message: The text to log.
        is_secret: If True, log to DM secrets (players don't see this).
    """
    session_log, secrets_log = get_log_paths()
    log_file = secrets_log if is_secret else session_log
    prefix = "[SECRET]" if is_secret else "[PUBLIC]"
    
    dm_utils.log_to_file(log_file, f"{prefix} {message}")
    
    base_resp = f"Logged to {'secrets' if is_secret else 'public'} log."
    
    if DEBUG_MODE:
        return f"[DEBUG] Written to {log_file}: {base_resp}"
        
    return base_resp

@mcp.tool()
def read_campaign_log(log_type: str) -> str:
    """
    Reads the full content of a specified log file.
    log_type: 'session', 'secrets', or 'world'.
    """
    return dm_utils.read_campaign_log(log_type)

@mcp.tool()
def list_sessions() -> str:
    """
    Lists all session directories in the active campaign.
    Shows which files exist in each session and which is current.
    Call this before read_full_session to discover available sessions.
    """
    return dm_utils.list_sessions()

@mcp.tool()
def read_full_session(session_name: str = "current") -> str:
    """
    Reads ALL log files from a specific session (session_log, secrets_log,
    and full_archive) combined into one response. Use this to fully recap
    a session's events, DM secrets, and raw chronological log.
    Args:
        session_name: e.g. "session_3" or "current" for the active session.
    """
    return dm_utils.read_session(session_name)

@mcp.tool()
def validate_action(action: str, character_name: str) -> str:
    """
    Validates a player's proposed action against the rules and their character state.
    Returns "VALID", "WARNING: <reason>", or "INVALID: <reason>".
    """
    return dm_utils.validate_game_mechanic(action, character_name)

@mcp.tool()
def generate_name(race: str = "any") -> str:
    """
    Generates a random fantasy name.
    race: "elf", "dwarf", "human", "hobbit", "place", or "any".
    """
    return dm_utils.generate_random_name(race)

@mcp.tool()
def end_session_and_compact(manual_summary: str = None) -> str:
    """
    Call this when the session ends. Summarizes the log, archives it, and creates a fresh start.
    If 'manual_summary' is provided, it uses that instead of generating one via Google API.
    """
    return dm_utils.summarize_and_compact_session_logic(manual_summary)

@mcp.tool()
def update_world_info(fact: str) -> str:
    """
    Records a PERMANENT fact about the world (NPCs, Locations, Politics).
    """
    return dm_utils.update_world_info(fact)

@mcp.tool()
def propose_scene_image(image_description: str) -> str:
    """
    Propose generating an image for the current scene.
    Does NOT generate immediately. Asks user for confirmation.
    """
    result = dm_utils.propose_image(image_description)
    return f"{result}\n(Note: In local mode, image generation display is limited depending on your client.)"

@mcp.tool()
def complete_setup_step() -> str:
    """
    Advances the Campaign Setup Wizard to the next step.
    """
    return dm_utils.advance_setup_step()

@mcp.tool()
def submit_character_sheet(character_name: str, details: str) -> str:
    """
    Saves a player's character sheet details during setup.
    """
    return dm_utils.save_character_sheet(character_name, details)

@mcp.tool()
def list_character_sheets() -> str:
    """
    Lists all saved character sheets for the active campaign.
    Use this to discover which characters exist before reading their details.
    """
    return dm_utils.list_character_sheets()

@mcp.tool()
def read_character_sheet(character_name: str) -> str:
    """
    Reads the full contents of a specific character's sheet.
    Args:
        character_name: The name of the character whose sheet to read.
    """
    return dm_utils.read_character_sheet(character_name)

@mcp.tool()
def lookup_past_session(query: str, session_name: str = None) -> str:
    """
    Research past events using Deep Memory.
    Modes:
    1. Search Summaries: If session_name is None, searches ALL past session summaries for the query.
       Example: query="Goblin King", session_name=None
    2. Read Detail: If session_name is provided, reads that full session's log.
       Example: query="IGNORED", session_name="session_4"
    """
    if session_name:
        return dm_utils.read_archived_history(session_name)
    else:
        return dm_utils.search_archived_summaries(query)

@mcp.tool()
def initialize_combat(entities: str) -> str:
    """
    Sets up the initial state for a combat encounter.
    entities: JSON string of list of dicts, e.g. '[{"name": "Goblin 1", "hp": 7, "max_hp": 7, "ac": 15}]'
    """
    import json
    try:
        data = json.loads(entities)
        return dm_utils.update_combat_state(data)
    except Exception as e:
        return f"Error parsing entities JSON: {e}"

@mcp.tool()
def track_combat_change(character_name: str, hp_change: int = 0, notes_update: str = None) -> str:
    """
    Updates a specific combatant's HP or notes.
    character_name: The name of the creature to update.
    hp_change: Amount to change HP (negative for damage, positive for healing).
    notes_update: New notes or status effects (e.g. "Stunned").
    """
    # Reuse the logic from common_tools since it has the parsing logic
    # But we can't easily import common_tools here due to potential circular deps if common_tools imports mcp_server (it doesn't, but let's be safe and copy logic or move it to dm_utils?)
    # Actually, dm_utils only has update_combat_state, not the parsing logic.
    # Let's import common_tools safely inside the function.
    import common_tools
    return common_tools.track_combat_change(character_name, hp_change, notes_update)

@mcp.tool()
def undo_last_message() -> str:
    """
    Removes the last (user, assistant) interaction from history.
    Use this if the AI made a mistake or the player wants to retcon their last action.
    """
    return dm_utils.undo_last_message()

if __name__ == "__main__":
    mcp.run()
