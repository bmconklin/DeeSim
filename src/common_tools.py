import dm_utils
import dnd_bridge
import os

# Shared State
DEBUG_MODE = False

def set_debug_mode(debug: bool) -> str:
    """
    Toggles Debug Mode.
    If True, dice rolls and rule lookups will return highly detailed system information.
    """
    global DEBUG_MODE
    DEBUG_MODE = debug
    state = "ENABLED" if debug else "DISABLED"
    return f"Debug Mode {state}."

# --- Tool Wrappers ---

def roll_dice(expression: str, purpose: str, is_secret: bool = False) -> str:
    """
    Rolls dice and logs result. 
    expression: e.g. '1d20+5'. 
    purpose: Reason for roll. 
    is_secret: If True, hides result from players in public log.
    """
    result = dm_utils.roll_dice(expression)
    if "error" in result:
        return result["error"]
        
    session_log, secrets_log = dm_utils.get_log_paths()
    log_file = secrets_log if is_secret else session_log
    log_type = "SECRET ROLL" if is_secret else "PUBLIC ROLL"
    
    log_message = f"**{log_type}** | Purpose: {purpose} | Result: {result['total']} ({result['rolls']} {result['modifier']})"
    dm_utils.log_to_file(log_file, log_message)
    
    return f"Rolled {expression} for {purpose}. Result: {result['total']}"

def log_event(message: str, is_secret: bool = False) -> str:
    """
    Logs a narrative event to the session log.
    message: The content to log.
    is_secret: If True, logs to secrets_log.md (hidden from players).
    """
    session_log, secrets_log = dm_utils.get_log_paths()
    log_file = secrets_log if is_secret else session_log
    prefix = "[SECRET]" if is_secret else "[PUBLIC]"
    dm_utils.log_to_file(log_file, f"{prefix} {message}")
    return "Logged event."

def search_dnd_rules(query: str) -> dict:
    """
    Search the official D&D 5e API for rules, spells, monsters, and items.
    Use this to find specific mechanics, stats, or descriptions.
    query: "fireball", "plate armor", "grappled condition"
    """
    return dnd_bridge.search_dnd_rules(query)

def verify_dnd_statement(statement: str) -> dict:
    """
    Check if a D&D rule statement is true using the API.
    statement: "Can wizards wear armor?", "How much damage does fireball do?"
    """
    return dnd_bridge.verify_dnd_statement(statement)

def find_monster_by_cr(min_cr: float, max_cr: float) -> dict:
    """
    Find monsters within a CR range.
    """
    return dnd_bridge.find_monster(min_cr, max_cr)

def start_new_session(summary_of_previous: str) -> str:
    """
    Archives current session and starts a new one.
    summary_of_previous: Recap of the last session.
    """
    return dm_utils.start_new_session_logic(summary_of_previous)

def request_player_roll(check_type: str, dc: int, consequence: str) -> str:
    """
    Logs a DC and Consequence/Fail State BEFORE asking the player to roll.
    check_type: What to roll (e.g. "Stealth").
    dc: Difficulty Class (e.g. 15).
    consequence: What happens on failure.
    """
    return dm_utils.request_player_roll_logic(check_type, dc, consequence)

def read_campaign_log(log_type: str) -> str:
    """
    Reads a campaign log file ('session', 'secrets', or 'world') to recall past events.
    log_type: 'session' (logs), 'secrets' (DM notes), or 'world' (locations/NPCs).
    """
    return dm_utils.read_campaign_log(log_type)

def update_world_info(fact: str) -> str:
    """
    Records a PERMANENT fact about the world (NPCs, Locations, Politics).
    fact: "The shopkeeper's name is Gundren."
    """
    return dm_utils.update_world_info(fact)

def end_session_and_compact(manual_summary: str = None) -> str:
    """
    Call this when the players say they are finishing the session for the night.
    It will:
    1. Read the current logs.
    2. Use AI to generate a concise summary (removing dice rolls/chatter) OR use manual_summary if provided.
    3. Archive the full detailed log.
    4. Replace the main log with the summary for the next session.
    """
    return dm_utils.summarize_and_compact_session_logic(manual_summary)

def propose_scene_image(image_description: str) -> str:
    """
    Propose generating an image for the current scene.
    DO NOT generate the image directly. This just asks the user for permission.
    Use this when describing a new location, monster, or epic moment.
    
    image_description: "A dark cavern with glowing blue mushrooms and a spider web."
    """
    result = dm_utils.propose_image(image_description)
    return f"{result}\nTell the user: 'I have a visual for this. Type `!show` to see it.'"

def validate_action(action: str, character_name: str) -> str:
    """
    Validates a player's proposed action against the rules and their character state.
    CALL THIS when a player attempts a significant move (casting a high-level spell, using a class feature).
    
    Returns "VALID", "WARNING: <reason>", or "INVALID: <reason>".
    If INVALID, you should ask the player to clarify or confirm before proceeding.
    """
    return dm_utils.validate_game_mechanic(action, character_name)

def complete_setup_step() -> str:
    """
    Call this when the goal of the current Setup Step (Intro/Roster/Sheets/Dice) is met.
    This advances the wizard to the next stage.
    """
    return dm_utils.advance_setup_step()

def submit_character_sheet(character_name: str, details: str) -> str:
    """
    Saves a player's character sheet details.
    Call this when a player provides their stats/backstory during setup.
    """
    return dm_utils.save_character_sheet(character_name, details)

def generate_name(race: str = "any") -> str:
    """
    Generates a random fantasy name.
    race: "elf", "dwarf", "human", "hobbit", or "any".
    """
    return dm_utils.generate_random_name(race)

# Helper to look up defunct rule search
def lookup_rule(query: str) -> str:
    """
    [DEPRECATED: Use search_dnd_rules instead if possible]
    Searches the local rules text for a query to prevent hallucinations.
    """
    rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_rules.txt")
    return dm_utils.search_rules(query, rules_path)
