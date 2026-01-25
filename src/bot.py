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
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import google.genai as genai
from google.genai import types

# Setup Gemini Client
# Client init moved to llm_bridge call later

# Setup Slack
app = App(token=os.environ["SLACK_BOT_TOKEN"])

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
    propose_scene_image,
    validate_action,
    complete_setup_step, # NEW
    submit_character_sheet # NEW
]

# Load System Prompt
def get_system_instruction():
    campaign_root = dm_utils.CAMPAIGN_ROOT
    prompt_path = os.path.join(campaign_dir_from_root(campaign_root), "system_prompt.txt")
    
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            return f.read()
    else:
        return "You are a Dungeon Master. Use the tools provided to run the game."

def campaign_dir_from_root(root):
    return root

import llm_bridge

# Initialize Chat Session via Bridge (Handles Google vs Local)
# We create a new chat session here, but ideally we persists history per slack thread?
# For now, we keep a global single-threaded memory as implied by "one campaign".
# If valid history persistence is needed, we'd need to manage history manually.

# Allow user to configure model name (e.g. for paid tiers or specific versions)
model_name = os.environ.get("MODEL_NAME", "gemini-2.5-flash")
print(f"✨ Connecting to Model: {model_name} (via Bridge)")

# Load history if available
history_data = dm_utils.load_chat_snapshot()
print(f"✨ Loaded {len(history_data)} messages from history.")

chat = llm_bridge.get_chat_session(
    model_name=model_name,
    history=history_data,
    tools=tools_list,
    system_instruction=get_system_instruction()
)

# --- Slack Handlers ---

import json
import re

# --- Access Control Helpers ---

class PermissionsManager:
    def __init__(self, file_path="permissions.json"):
        self.file_path = file_path
        self.load()
        
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {"users": [], "channels": []}
            
    def save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=2)
            
    def add_user(self, user_id):
        if user_id not in self.data["users"]:
            self.data["users"].append(user_id)
            self.save()
            return True
        return False
        
    def remove_user(self, user_id):
        if user_id in self.data["users"]:
            self.data["users"].remove(user_id)
            self.save()
            return True
        return False

    def get_allowed_users(self):
        return self.data["users"]

permissions = PermissionsManager()

def is_allowed(user_id=None, channel_id=None):
    # 1. Check Env Vars (Static)
    env_allowed_users = os.environ.get("ALLOWED_USER_IDS", "")
    env_allowed_channels = os.environ.get("ALLOWED_CHANNEL_IDS", "")
    
    # If NO access control is set at all (Env or JSON), allow all
    json_users = permissions.get_allowed_users()
    
    if not env_allowed_users and not env_allowed_channels and not json_users:
        return True

    # 2. Check Allow Lists
    # Users
    allowed = False
    if env_allowed_users:
        if user_id and user_id in [u.strip() for u in env_allowed_users.split(",")]:
            allowed = True
    
    if user_id and user_id in json_users:
        allowed = True
        
    # If we have user restrictions and the user wasn't found -> Block
    if (env_allowed_users or json_users) and not allowed:
        return False

    # Channels
    if env_allowed_channels:
        channels_list = [c.strip() for c in env_allowed_channels.split(",")]
        if channel_id and channel_id not in channels_list:
            return False
            
    return True

# --- Slack Handlers ---

@app.message(re.compile("^!admin"))
def handle_admin_commands(message, say):
    user_id = message['user']
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
    result = dm_utils.clear_pending_image()
    say(f"🗑️ {result}")

    result = dm_utils.clear_pending_image()
    say(f"🗑️ {result}")

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
            # We construct a mini-prompt for the model
            # Note: We can reuse the existing 'chat' object if we want context, 
            # or just a direct generation tool if we had one exposed.
            # Since we don't have a direct 'generate_text' tool exposed to the bot context itself easily here without full turn,
            # we will just pretend this is a normal user prompt asking for a name.
            # BUT wait, handle_app_mentions does the heavy lifting.
            # Here we are in a specific listener.
            # Let's call Gemini directly via dm_utils helper if we want, or just ask the user to ask the bot.
            # Actually, let's add a simple helper in dm_utils for raw generation to keep it clean.
            
            # For now, let's just use the `dm_utils.generate_random_name` fallback logic?
            # No, dm_utils returned None.
            
            # Let's add a quick direct generation call here using the client if possible?
            # Or better, just use the `chat` interface.
            
            # Simpler: Just tell the user to ask the bot directly if it's exotic.
            # "I don't have a rigid database for {race}, but you can ask me directly: '@DeeSim give me 5 goblin names'."
            
            # User REQUESTED: "leave it to the bot's discretion"
            # So we should probably do it.
            
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                say(f"❌ Custom names require GOOGLE_API_KEY. See README.md.")
                return

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=os.environ.get("MODEL_NAME", "gemini-2.5-flash"),
                contents=f"Generate a single creative fantasy name for a {race}. Return ONLY the name."
            )
            say(f"✨ AI-Generated Name ({race}): *{response.text.strip()}*")
            
        except Exception as e:
            say(f"❌ Failed to generate name: {e}")

@app.message(re.compile("^!iam"))
def handle_iam_command(message, say):
    user_id = message['user']
    text = message['text']
    
    # Format: !iam <Character Name>
    match = re.search(r"!iam\s+(.+)", text, re.IGNORECASE)
    if not match:
        say("Usage: `!iam <Character Name>` (e.g. `!iam Grognak`)")
        return
        
    char_name = match.group(1).strip()
    result = dm_utils.register_player(user_id, char_name)
    say(result)


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
                    # Create Part object
                    parts.append(types.Part.from_bytes(data=image_data, mime_type=mimetype))
                    logger.info("✅ Image downloaded and converted to Part.")
                except Exception as e:
                    logger.error(f"Failed to create image part: {e}")
            else:
                logger.error("Failed to download image data.")
                
    return parts

@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    user_id = body['event']['user']
    channel_id = body['event']['channel']
    event = body['event']
    
    if not is_allowed(user_id, channel_id):
        logger.info(f"Blocked access from User: {user_id} in Channel: {channel_id}")
        say(f"🔒 You are not in the Book of Allowed Heroes. Ask the DM (`!admin allow <@{user_id}>`).")
        return

    logger.info(f"Received mention from {user_id}")
    user_text = event["text"]
    
    # Process Attachments (Images)
    image_parts = process_attachments(event, logger)
    if image_parts:
        logger.info(f"Processing {len(image_parts)} images with request.")
    
    # Context Injection: Player Name
    char_name = dm_utils.get_character_name(user_id)
    if char_name != "Unknown Hero":
        user_text = f"(Character: {char_name}) {user_text}"
    
    # Context Injection: Passive Buffer (Background Chatter)
    buffered_context = dm_utils.get_and_clear_context_buffer()
    if buffered_context:
        user_text = f"[Background Context - Untagged Conversation]:\n{buffered_context}\n\n[Direct Interaction]:\n{user_text}"
        
    # Context Injection: Attendance / New Session Check
    hours_since = dm_utils.get_hours_since_last_message()
    if hours_since > 4.0: # 4 hours gap implies new session
         system_note = f"[System Note: It has been {hours_since:.1f} hours since the last game interaction. This is likely a new session. Please welcome the players back, mention the break, and ask for a roll call to see who is present before continuing.]"
         user_text = f"{system_note}\n\n{user_text}"

    # Context Injection: Campaign Setup Wizard
    setup_step = dm_utils.get_setup_step()
    if setup_step < 4:
         setup_instructions = dm_utils.get_setup_instructions(setup_step)
         user_text = f"{setup_instructions}\n\n{user_text}"

    try:
        # Construct content list (Text + Images)
        content = [user_text]
        if image_parts:
            content.extend(image_parts)
            
        response = chat.send_message(content)
        say(response.text)
        
        try:
            history_snapshot = []
            for msg in chat.get_history():
                if hasattr(msg, "model_dump"):
                     history_snapshot.append(msg.model_dump(mode='json'))
                elif hasattr(msg, "to_dict"):
                     history_snapshot.append(msg.to_dict())
            dm_utils.save_chat_snapshot(history_snapshot)
        except Exception as h_err:
            logger.error(f"Failed to save history: {h_err}")
            
    except Exception as e:
        error_str = str(e)
        logger.error(f"Gemini Error: {error_str}")
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            say("⏳ The magical winds are calm (Rate Limit Exceeded). Please wait a moment and try again.")
        else:
            say(f"I encountered a magical disturbance (Error: {error_str})")

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
    text = message.get("text")
    
    # --- DM LOGIC (Active) ---
    if channel_type == "im":
        if not is_allowed(user_id, channel_id):
            say("🔒 Access Denied.")
            return

        logger.info(f"Received DM from {user_id}")
        
        # Process Attachments (Images)
        image_parts = process_attachments(message, logger)
        
        # Context Injection: Player Name
        char_name = dm_utils.get_character_name(user_id)
        if char_name != "Unknown Hero":
            text = f"(Character: {char_name}) {text}"
            
        try:
            # Construct content list (Text + Images)
            content = [text]
            if image_parts:
                content.extend(image_parts)

            response = chat.send_message(content)
            say(response.text)
            
            try:
                history_snapshot = []
                for msg in chat.get_history():
                    if hasattr(msg, "model_dump"):
                         history_snapshot.append(msg.model_dump(mode='json'))
                    elif hasattr(msg, "to_dict"):
                         history_snapshot.append(msg.to_dict())
                
                dm_utils.save_chat_snapshot(history_snapshot)
            except Exception as h_err:
                logger.error(f"Failed to save history: {h_err}")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini Error: {error_str}")
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                say("⏳ The magical winds are calm (Rate Limit Exceeded). Please wait a moment and try again.")
            else:
                say(f"I encountered a magical disturbance (Error: {error_str})")
        return

    # --- CHANNEL BUFFER LOGIC (Passive) ---
    # We only buffer if it is NOT a mention (mentions are handled by app_mention).
    # Bolt doesn't give us a clean "is_mention" flag here easily without checking text.
    # But usually app_mention fires separate from message? 
    # Actually `message` fires for everything script-wise if subbed.
    # We depend on the User NOT tagging the bot if they want it buffered.
    
    # Check if text contains bot user ID? 
    # Actually, simpler: just buffer it. If it WAS a mention, the app_mention handler will ALSO see it.
    # If we buffer the mention too, we just duplicate context slightly?
    # Let's try to avoid buffering mentions if possible to reduce noise.
    # But we don't know our own Bot ID easily here without calling auth.test.
    # For now, buffer everything in channels. The app_mention handler will consume the buffer.
    # If the buffer includes the trigger message, the LLM will see:
    # [Context] User: @Bot hello
    # [Request] User: @Bot hello
    # That is fine.
    
    if is_allowed(user_id, channel_id):
        char_name = dm_utils.get_character_name(user_id)
        author_name = char_name if char_name != "Unknown Hero" else f"User_{user_id}"
        dm_utils.append_to_context_buffer(author_name, text)

if __name__ == "__main__":
    print("🤖 Agentic DM is listening via Socket Mode...")
    print(f"Campaign Root: {dm_utils.CAMPAIGN_ROOT}")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
