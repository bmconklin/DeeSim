import os
import sys
from dotenv import load_dotenv

# Load env vars BEFORE importing dm_utils to ensure CAMPAIGN_ROOT is picked up
load_dotenv()

# Check for required Slack keys (Google Key is optional for Local Mode)
if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_APP_TOKEN"):
    print("Error: Missing secrets in .env file (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)")
    print("Please create a .env file with these keys.")
    sys.exit(1)

import dm_utils
import dnd_bridge
import common_tools
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import google.genai as genai
from google.genai import types

# Setup Gemini Client
# Client init moved to llm_bridge call later

# Setup Slack
# Setup Slack
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Fetch Bot Identity Global
BOT_NAME = "Dungeon Master"
BOT_ID = None
try:
    auth_res = app.client.auth_test()
    BOT_ID = auth_res["user_id"]
    BOT_NAME = auth_res["user"]
    print(f"🤖 Bot Identity: {BOT_NAME} ({BOT_ID})")
except Exception as e:
    print(f"⚠️ Failed to init bot identity: {e}")

# --- Tool Wrappers for Gemini ---

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

def lookup_rule(query: str) -> str:
    """
    [DEPRECATED: Use search_dnd_rules instead if possible]
    Searches the local rules text for a query to prevent hallucinations.
    query: The term to search for (e.g. 'grapple').
    """
    rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_rules.txt")
    return dm_utils.search_rules(query, rules_path)

# --- New D&D API Tools ---
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

def send_dm(character_name: str, message: str) -> str:
    """
    Sends a PRIVATE Direct Message to a specific player.
    Use this for:
    - Secret information only one player knows.
    - Perception checks that others missed.
    - Private telepathic communication.
    
    character_name: The name of the character (e.g. "Grog").
    message: The content of the private message.
    """
    user_id = dm_utils.get_user_id_by_character_name(character_name)
    if not user_id:
        return f"Error: Could not find player for character '{character_name}'. Have they registered with `!iam`?"
        
    try:
        app.client.chat_postMessage(channel=user_id, text=message)
        return f"Successfully sent private message to {character_name}."
    except Exception as e:
        return f"Failed to send DM: {e}"

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
    
def generate_scene_image(image_description: str) -> str:
    """
    GENERATES a visual illustration for the current scene.
    Call this whenever the user asks for an image OR when you describe a new location.
    
    The system will handle the actual generation.
    
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

def generate_name(race: str = "any", count: int = 1) -> str:
    """
    Generates random fantasy names for characters, locations, or items.
    race: "elf", "dwarf", "human", "hobbit", "place" (towns), or "any".
    count: How many names to generate (suggested: 5-10 for a pool of options). 

    UNIVERSAL RULE: When you need a name, ALWAYS generate a pool of options (count=5 or more).
    Evaluation: Review the generated list and select the ONE name that best fits the current tone, setting, and context.
    Final Call: You are the DM. Do not ask the players to pick; you make the executive decision and announce it.
    """
    return dm_utils.generate_random_name(race, count)

# --- Model Initialization ---
# Define tools config for new SDK
tools_list = [
    roll_dice, 
    log_event, 
    lookup_rule, 
    search_dnd_rules, 
    verify_dnd_statement, 
    find_monster_by_cr, 
    start_new_session, 
    request_player_roll, 
    read_campaign_log,
    send_dm,
    end_session_and_compact,
    update_world_info,
    generate_scene_image,
    validate_action,
    complete_setup_step, # NEW
    submit_character_sheet, # NEW
    generate_name,
    common_tools.initialize_combat,
    common_tools.track_combat_change
]

# Load System Prompt
def get_system_instruction():
    return dm_utils.get_system_instruction()

def campaign_dir_from_root(root):
    return root

# --- Setup Game Engine ---
from core.engine import GameEngine
from core.permissions import is_allowed, permissions

# Initialize Engine with Tools (Multi-tenant)
engine = GameEngine(
    tools_list=tools_list
)

# --- Slack Handlers ---

# Function to process attachments (Images) for Slack
def process_attachments(event_data, logger):
    """
    Checks for files in the event, downloads images, and returns Gemini Parts.
    """
    files = event_data.get("files", [])
    if not files:
        return []
        
    parts = []
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    
    for file in files:
        mimetype = file.get("mimetype", "")
        if mimetype.startswith("image/"):
            url_private = file.get("url_private")
            logger.info(f"📸 Found image: {file.get('name')} ({mimetype})")
            
            image_data = dm_utils.download_slack_file(url_private, slack_token)
            if image_data:
                try:
                    import google.genai.types as types
                    # Create Part object
                    parts.append(types.Part.from_bytes(data=image_data, mime_type=mimetype))
                    logger.info("✅ Image downloaded and converted to Part.")
                except Exception as e:
                    logger.error(f"Failed to create image part: {e}")
            else:
                logger.error("Failed to download image data.")
                
    return parts

@app.message(re.compile("^!help"))
def handle_help_command(message, say):
    """
    Lists available commands.
    """
    help_text = (
        "📜 **Dungeon Master Commands** 📜\n\n"
        "**Player Commands:**\n"
        "`!iam <Character Name>` - Register your character name for this channel.\n"
        "`!name <race>` - Generate a random name for a specific race.\n"
        "`!show` - Approve and post a generated image.\n"
        "`!hide` - Discard a generated image.\n"
        "`!help` - Show this help message.\n\n"
        "**Session Commands:**\n"
        "`!wrapup` - End current session and generate summary.\n"
        "`!startsession` - Start a new session (uses summary from last wrapup).\n\n"
        "**Admin Commands:**\n"
        "`!admin bind <campaign_name>` - Bind this channel to a specific campaign.\n"
        "`!admin list` - List allowed users.\n"
        "`!admin allow <@user>` - Allow a user to interact with the bot.\n"
        "`!admin deny <@user>` - Block a user.\n"
    )
    say(help_text)

# Helper for User Names
user_cache = {}
def fetch_user_name(user_id):
    if user_id in user_cache:
        return user_cache[user_id]
    try:
        result = app.client.users_info(user=user_id)
        if result["ok"]:
            user = result["user"]
            # Prefer display name, fallback to real name
            name = user["profile"].get("display_name") or user.get("real_name") or user.get("name")
            user_cache[user_id] = name
            return name
    except Exception as e:
        # Log once or verbose
        print(f"⚠️ Failed to fetch user name for {user_id}: {e}")
    
    # Fallback so the Engine doesn't see None
    return f"User <{user_id}>"

@app.message(re.compile("^!admin"))
def handle_admin_commands(message, say):
    user_id = message['user']
    channel_id = message['channel']
    
    # Resolve Campaign Context
    campaign_name = dm_utils.get_campaign_for_channel("slack", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    
    try:
        admin_id = os.environ.get("ADMIN_USER_ID")
        if not admin_id or user_id != admin_id:
            say(f"⛔ You are not the Dungeon Master (Admin ID: {admin_id}).")
            return
            
        text = message['text']
        parts = text.split()
        
        if len(parts) < 2:
            say("Usage: `!admin allow @user`, `!admin deny @user`, `!admin list`")
            return
            
        command = parts[1]
        
        if command == "list":
            users = permissions.get_allowed_users()
            say(f"**Allowed Users**:\n{users if users else 'None (Public Mode if env is empty)'}")
            return
            
        if command in ["allow", "deny"]:
            # Extract user ID from tag <@U12345>
            target_ids = re.findall(r"<@([A-Z0-9]+)>", text)
            if not target_ids:
                say("Please tag the user(s) you want to modify.")
                return
                
            for tid in target_ids:
                if command == "allow":
                    permissions.add_user(tid)
                    say(f"✅ Added <@{tid}> to allowed list.")
                else:
                    permissions.remove_user(tid)
                    say(f"❌ Removed <@{tid}> from allowed list.")
            return
    
        elif command == "bind":
            if len(parts) < 3:
                say("Usage: `!admin bind <campaign_name>`")
                return
            campaign_name = parts[2]
            dm_utils.bind_channel_to_campaign("slack", message['channel'], campaign_name)
            say(f"✅ Success! Channel is now bound to campaign `{campaign_name}`.")
            return
    finally:
        if token:
            dm_utils.active_campaign_ctx.reset(token)

@app.message(re.compile("^!show"))
def handle_show_command(message, say, logger):
    """
    User approves the pending image generation.
    """
    channel_id = message['channel']
    say("🎨 Painting the scene... (This takes ~5 seconds)")
    
    image_bytes, result = dm_utils.generate_image_from_pending()
    
    if image_bytes:
        try:
            app.client.files_upload_v2(
                channel=channel_id,
                file=image_bytes,
                filename="scene_visual.png",
                title=result, # The prompt
                initial_comment=f"Visual for: *{result}*"
            )
        except Exception as e:
            say(f"❌ Upload Failed: {e}")
    else:
        say(f"❌ Generation Failed: {result}")

@app.message(re.compile("^!hide"))
def handle_hide_command(message, say):
    """
    User rejects the pending image.
    """
    say(f"🗑️ {result}")


@app.message(re.compile("^!wrapup"))
def handle_wrapup_command(message, say):
    # Context wrapper
    channel_id = message['channel']
    campaign_name = dm_utils.get_campaign_for_channel("slack", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    else:
        say("❌ This channel is not bound to a campaign. Run `!admin bind <name>` first.")
        return

    try:
        say("📜 Compacting session log and generating summary...")
        result = dm_utils.summarize_and_compact_session_logic()
        say(result)
        say("✅ Session wrapped! Type `!startsession` to begin the next chapter.")
    except Exception as e:
        say(f"❌ Wrap-up failed: {e}")
    finally:
        if token: dm_utils.active_campaign_ctx.reset(token)

@app.message(re.compile("^!startsession"))
def handle_startsession_command(message, say):
    # Context wrapper
    channel_id = message['channel']
    campaign_name = dm_utils.get_campaign_for_channel("slack", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    else:
        say("❌ This channel is not bound to a campaign. Run `!admin bind <name>` first.")
        return

    try:
        say("🌅 Initializing new session...")
        
        # 1. Read the summary from current session log
        # Note: If !wrapup was just run, this reads the 'previous' session log which is technically the 'current' one on disk before session increment?
        # No, start_new_session_logic moves current to session_X.
        # So we read the log that exists NOW. 
        log_path, _ = dm_utils.get_log_paths()
        
        summary = "Session ended without automated summary."
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                content = f.read()
            if "## Summary" in content:
                try:
                    summary = content.split("## Summary")[1].split("##")[0].strip()
                except IndexError:
                    pass

        # 2. Start new session
        result = dm_utils.start_new_session_logic(summary)
        say(f"🎉 {result}")
        
    except Exception as e:
        say(f"❌ Failed to start new session: {e}")
    finally:
        if token: dm_utils.active_campaign_ctx.reset(token)

@app.message(re.compile("^!recap"))
def handle_recap_command(message, say):
    """
    Forcefully retrieves the log for a specific session (or current) and summarizes it.
    Usage: !recap or !recap session_4
    """
    # Context wrapper
    channel_id = message['channel']
    campaign_name = dm_utils.get_campaign_for_channel("slack", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    else:
        say("❌ This channel is not bound to a campaign.")
        return

    try:
        parts = message.get("text", "").split()
        target_session = parts[1] if len(parts) > 1 else None

        root = dm_utils.get_campaign_root()
        
        if target_session:
            # Look for specific session folder
            log_path = os.path.join(root, target_session, "session_log.md")
        else:
            # Use current
            log_path, _ = dm_utils.get_log_paths()

        if not os.path.exists(log_path):
            say(f"❌ Could not find log file at `{log_path}`.")
            return

        with open(log_path, "r") as f:
            content = f.read()

        # 1. Show user (truncated)
        say(f"📜 **Recap from {os.path.basename(os.path.dirname(log_path))}**:\n\n{content[:1000]}...\n\n*(Injecting full log into AI memory...)*")
        
        # 2. Feed to Agent to rebuild context
        user_id = message.get("user")
        user_name = fetch_user_name(user_id)
        
        # Construct a system-style injection message
        injection_text = (
            f"[SYSTEM NOTICE: The user has requested to LOAD the following session log into your active memory. "
            f"Read this context and acknowledge it, but do not repeat it back fully.]\n\n"
            f"--- START OF RECAP ({os.path.basename(os.path.dirname(log_path))}) ---\n"
            f"{content}\n"
            f"--- END OF RECAP ---"
        )
        
        response_text = engine.process_message(
            user_id=user_id,
            user_name=user_name,
            message_text=injection_text,
            platform_id="slack",
            attachments=[],
            channel_id=channel_id,
            server_id=message.get("team")
        )
        say(f"🤖 {response_text}")
            
    except Exception as e:
        say(f"❌ Recap failed: {e}")
    finally:
        if token: dm_utils.active_campaign_ctx.reset(token)



@app.message(re.compile("^!name"))
def handle_name_command(message, say):
    """
    !name <race>
    """
    text = message['text']
    parts = text.split()
    race = "any"
    if len(parts) > 1:
        race = parts[1]
    
    name = dm_utils.generate_random_name(race)
    
    if name:
        say(f"🎲 Random Name ({race}): *{name}*")
    else:
        # Fallback to LLM if library doesn't support it
        say(f"🎲 Generating unique {race} name... (One moment)")
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                say(f"❌ Custom names require GOOGLE_API_KEY. See README.md.")
                return
            
            # The GameEngine will handle LLM calls for name generation if dm_utils doesn't have it.
            # For now, we'll just indicate failure if dm_utils doesn't return a name.
            say(f"❌ Failed to generate name for '{race}' using available tools. Try asking the bot directly: '@DeeSim generate a {race} name'.")
            
        except Exception as e:
            say(f"❌ Failed to generate name: {e}")

@app.message(re.compile("^!iam"))
def handle_iam_command(message, say):
    user_id = message['user']
    channel_id = message['channel']
    text = message['text']
    
    # Resolve Campaign Context
    campaign_name = dm_utils.get_campaign_for_channel("slack", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    
    try:
        match = re.search(r"!iam\s+(.+)", text, re.IGNORECASE)
        if not match:
            say("Usage: `!iam <Character Name>` (e.g. `!iam Grognak`)")
        else:
            char_name = match.group(1).strip()
            result = dm_utils.register_player(user_id, char_name)
            say(result)
    finally:
        if token:
            dm_utils.active_campaign_ctx.reset(token)

@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    user_id = body['event']['user']
    channel_id = body['event']['channel']
    event = body['event']
    
    logger.info(f"Received mention from {user_id}")
    user_text = event["text"]
    
    # Strip the bot's mention from the text to avoid confusion
    # Slack mentions look like <@U12345>
    if BOT_ID and f"<@{BOT_ID}>" in user_text:
        user_text = user_text.replace(f"<@{BOT_ID}>", "").strip()

    # Process Attachments (Images)
    image_parts = process_attachments(event, logger)
    
    # Delegate to Engine
    # Fetch real user name for better UX
    user_name = fetch_user_name(user_id)
    
    # Inject Bot Identity Context
    final_text = f"[Context: You are '{BOT_NAME}'. Address the user as '{user_name}'.]\n{user_text}"
    
    response_text = engine.process_message(
        user_id=user_id,
        user_name=user_name,
        message_text=final_text,
        platform_id="slack",
        attachments=image_parts,
        channel_id=channel_id,
        server_id=body.get("team_id")
    )
    
    say(response_text)

@app.message(".*")
def handle_message_events(message, say, logger):
    """
    Handles all message events. 
    1. If DM ('im'): Respond (Active)
    2. If Channel ('channel'): Buffer (Passive) - UNLESS it's a mention (handled by app_mention)
    """
    
    # 1. Ignore Admin Commands (already handled)
    if message.get("text", "").startswith("!admin") or message.get("text", "").startswith("!iam"):
        return

    # 2. Ignore Bot's own messages (Slack usually filters, but safety first)
    if message.get("subtype") == "bot_message" or message.get("bot_id"):
        return

    channel_type = message.get("channel_type")
    user_id = message.get("user")
    channel_id = message.get("channel")
    server_id = message.get("team") # Slack Team ID
    text = message.get("text")
    
    # --- DM LOGIC (Active) ---
    if channel_type == "im":
        logger.info(f"Received DM from {user_id}")
        
        # Process Attachments (Images)
        image_parts = process_attachments(message, logger)
        
        user_name = fetch_user_name(user_id)

        # Inject Bot Identity Context
        final_text = f"[Context: You are '{BOT_NAME}'. Address the user as '{user_name}'.]\n{text}"

        response_text = engine.process_message(
            user_id=user_id,
            user_name=user_name,
            message_text=final_text,
            platform_id="slack",
            attachments=image_parts,
            channel_id=channel_id,
            server_id=server_id
        )
        say(response_text)
        return

    # --- CHANNEL BUFFER LOGIC (Passive) ---
    # Only buffer if allowed
    user_name = fetch_user_name(user_id)
    engine.buffer_message(
        user_id=user_id,
        user_name=user_name,
        message_text=text,
        platform_id="slack",
        channel_id=channel_id,
        server_id=server_id
    )

if __name__ == "__main__":
    print("🤖 Agentic DM (Slack) is listening via Socket Mode...")
    # Dynamic root (default)
    print(f"Default Campaign Root: {dm_utils.get_campaign_root()}")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
