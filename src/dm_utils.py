import os
import random
import requests
import json
import datetime
import re
try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    genai = None # Handle missing dependency for pure local/offline mode
import fantasynames as fn

def download_slack_file(url: str, token: str) -> bytes:
    """
    Downloads a private Slack file using the Bot Token.
    Manually handles redirects to ensure Authorization header persists.
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Allow redirects but use a session or just simple get? 
        # Requests drops auth headers on cross-domain redirects.
        # Let's try allow_redirects=True (default) but verify behavior.
        # Actually, let's assume it IS redirecting to a CDN.
        
        # We will try a loop to handle it explicitly if needed, 
        # but often just passing valid headers to the *final* URL is what's needed.
        # However, we don't know the final URL.
        
        response = requests.get(url, headers=headers, allow_redirects=True)
        
        # Check if we got redirected to a login page (HTML) despite code 200
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            # If we were redirected, the header might have been dropped.
            if response.history:
                # Retry the FINAL url with the headers explicitly
                response = requests.get(response.url, headers=headers)
        
        if response.status_code == 200:
            data = response.content
            # Final check for HTML which implies failed auth/redirect
            if "text/html" in response.headers.get("Content-Type", ""):
                 print("ERROR: Received HTML content. Possible missing 'files:read' scope.")
                 return None
            return data
        else:
            print(f"Error downloading file: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None
def get_chat_history_path():
    session_dir = get_current_session_dir()
    return os.path.join(session_dir, "chat_history.json")

def load_chat_snapshot() -> list:
    """
    Loads proper JSON history for the API.
    """
    path = get_chat_history_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def prune_empty_fields(data):
    """Recursively remove empty dictionaries, lists, or None values."""
    if isinstance(data, dict):
        return {k: prune_empty_fields(v) for k, v in data.items() if v not in [None, "", [], {}]}
    elif isinstance(data, list):
        return [prune_empty_fields(v) for v in data if v not in [None, "", [], {}]]
    else:
        return data

def save_chat_snapshot(history_data: list):
    """
    Overwrites chat history with the latest list of dicts.
    Prunes empty fields (None, [], {}) to keep the file lean.
    """
    path = get_chat_history_path()
    # Ensure directory exists just in case
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Serialize objects if needed
    serializable_history = []
    for msg in history_data:
        if isinstance(msg, dict):
            serializable_history.append(msg)
        elif hasattr(msg, "model_dump"):
            serializable_history.append(msg.model_dump(mode='json'))
        elif hasattr(msg, "to_dict"):
            serializable_history.append(msg.to_dict())
        else:
            # Fallback for weird objects, try __dict__ or just str? 
            # Better to skip or basic str to avoid crash
            try:
                serializable_history.append(msg.__dict__)
            except:
                serializable_history.append({"role": "error", "parts": [str(msg)]})

    # Prune history
    clean_history = [prune_empty_fields(msg) for msg in serializable_history]
    
    with open(path, "w") as f:
        json.dump(clean_history, f, indent=2)

def roll_dice(expression: str) -> dict:
    """
    Parses a dice expression (e.g., '1d20+5') and returns the detailed result.
    Supported formats: NdM, NdM+X, NdM-X
    """
    expression = expression.lower().replace(" ", "")
    match = re.match(r"(\d+)d(\d+)([\+\-]\d+)?", expression)
    
    if not match:
        return {"error": f"Invalid dice expression: {expression}"}
    
    num_dice = int(match.group(1))
    die_type = int(match.group(2))
    modifier_str = match.group(3)
    
    modifier = 0
    if modifier_str:
        modifier = int(modifier_str)
        
    rolls = [random.randint(1, die_type) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    
    return {
        "expression": expression,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "timestamp": datetime.datetime.now().isoformat()
    }

def log_to_file(file_path: str, content: str):
    """
    Appends content to a file with a timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n[{timestamp}] {content}\n"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "a") as f:
        f.write(entry)

def search_rules(query: str, rules_file_path: str) -> str:
    """
    Simple keyword search in the rules file.
    Returns paragraphs containing the query.
    """
    if not os.path.exists(rules_file_path):
        return "Rules file not found."
        
    query = query.lower()
    results = []
    
    with open(rules_file_path, "r") as f:
        content = f.read()
        
    # Split by paragraphs (approximate with double newline)
    paragraphs = content.split("\n\n")
    
    for p in paragraphs:
        if query in p.lower():
            results.append(p)
            
    if not results:
        return f"No rules found regarding '{query}'."
        
    return "\n---\n".join(results[:3]) # Return top 3 matches

# --- Campaign & Session Management ---

CAMPAIGN_ROOT = os.environ.get("DM_CAMPAIGN_ROOT", os.path.join(os.getcwd(), "campaigns/default"))

def get_current_session_dir():
    current_session_file = os.path.join(CAMPAIGN_ROOT, "current_session.txt")
    if os.path.exists(current_session_file):
        with open(current_session_file, "r") as f:
            session_name = f.read().strip()
        return os.path.join(CAMPAIGN_ROOT, session_name)
    else:
        return CAMPAIGN_ROOT

def get_log_paths():
    session_dir = get_current_session_dir()
    session_log = os.path.join(session_dir, "session_log.md")
    secrets_log = os.path.join(session_dir, "secrets_log.md")
    return session_log, secrets_log

def start_new_session_logic(summary_of_previous: str) -> str:
    current_session_file = os.path.join(CAMPAIGN_ROOT, "current_session.txt")
    if not os.path.exists(current_session_file):
        return "Error: Could not find current_session.txt. Is this a valid campaign?"
        
    with open(current_session_file, "r") as f:
        current_name = f.read().strip()
        
    try:
        current_num = int(current_name.split("_")[1])
    except:
        current_num = 0
        
    next_num = current_num + 1
    next_session_name = f"session_{next_num}"
    next_session_dir = os.path.join(CAMPAIGN_ROOT, next_session_name)
    
    os.makedirs(next_session_dir, exist_ok=True)
    
    with open(os.path.join(next_session_dir, "session_log.md"), "w") as f:
        f.write(f"# Session Log: {next_session_name}\n\n")
        f.write(f"## Previously on...\n{summary_of_previous}\n\n")
        
    with open(os.path.join(next_session_dir, "secrets_log.md"), "w") as f:
        f.write(f"# DM Secrets: {next_session_name}\n\n")
        
    with open(current_session_file, "w") as f:
        f.write(next_session_name)
        
    return f"Successfully started {next_session_name}. Previous session archived."

def request_player_roll_logic(check_type: str, dc: int, consequence: str) -> str:
    session_log, secrets_log = get_log_paths()
    log_message = f"**WAITING FOR PLAYER** | Type: {check_type} | DC: {dc} | Fail Consequence: {consequence}"
    log_to_file(secrets_log, log_message)
    return "Logged DC and Consequence. You may now ask the player to roll."

# --- Player & Attendance Logic ---

def get_player_mapping_path():
    session_dir = get_current_session_dir()
    # Save mapping in the campaign root usually, but session dir is fine if we want per-campaign
    # Actually, player mapping is likely campaign-wide.
    return os.path.join(CAMPAIGN_ROOT, "player_mapping.json")

def load_player_mapping() -> dict:
    path = get_player_mapping_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_player_mapping(mapping: dict):
    path = get_player_mapping_path()
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)

def register_player(user_id: str, char_name: str) -> str:
    mapping = load_player_mapping()
    mapping[user_id] = char_name
    save_player_mapping(mapping)
    return f"Registered <@{user_id}> as **{char_name}**."

def get_character_name(user_id: str) -> str:
    mapping = load_player_mapping()
    return mapping.get(user_id, "Unknown Hero")

def get_user_id_by_character_name(char_name: str) -> str:
    """
    Reverse lookup: Find Slack User ID from Character Name.
    Case-insensitive partial match.
    """
    mapping = load_player_mapping()
    char_name_lower = char_name.lower().strip()
    
    for uid, name in mapping.items():
        if name.lower().strip() == char_name_lower:
            return uid
            
    # If no exact match, try partial
    for uid, name in mapping.items():
        if char_name_lower in name.lower():
            return uid
            
    return None

def get_hours_since_last_message() -> float:
    """
    Returns hours since the last logged message in chat_history.json.
    Returns 999.0 if no history exists.
    """
    history = load_chat_snapshot()
    if not history:
        return 999.0
        
    # Try to find the last valid timestamp. 
    # Our simple history dump might not have timestamps unless we add them, 
    # OR we rely on file modification time of chat_history.json?
    # File mod time is safer/easier if we save on every turn.
    
    path = get_chat_history_path()
    if not os.path.exists(path):
        return 999.0
        
    mod_time = os.path.getmtime(path)
    current_time = datetime.datetime.now().timestamp()
    
    delta_seconds = current_time - mod_time
    return delta_seconds / 3600.0

def get_context_buffer_path():
    session_dir = get_current_session_dir()
    return os.path.join(session_dir, "context_buffer.json")

def append_to_context_buffer(author: str, text: str):
    """
    Appends a message to the context buffer.
    """
    path = get_context_buffer_path()
    buffer = []
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                buffer = json.load(f)
        except:
            buffer = []
            
    # Add new message
    timestamp = datetime.datetime.now().strftime("%H:%M")
    buffer.append(f"[{timestamp}] {author}: {text}")
    
    # Save
    with open(path, "w") as f:
        json.dump(buffer, f, indent=2)

def get_and_clear_context_buffer() -> str:
    """
    Returns the accumulated context as a single string and clears the file.
    """
    path = get_context_buffer_path()
    if not os.path.exists(path):
        return ""
        
    try:
        with open(path, "r") as f:
            buffer = json.load(f)
    except:
        return ""
        
    if not buffer:
        return ""
        
    # Clear file
    os.remove(path)
    
    
    return "\n".join(buffer)

def read_campaign_log(log_type: str) -> str:
    """
    Reads the full content of a specified log file.
    log_type: 'session', 'secrets', or 'world'.
    """
    session_log, secrets_log = get_log_paths()
    campaign_dir = CAMPAIGN_ROOT # From global var
    
    if log_type == "session":
        path = session_log
    elif log_type == "secrets":
        path = secrets_log
    elif log_type == "world":
        # World info is in campaign root
        path = os.path.join(campaign_dir, "world_info.md")
    else:
        return "Invalid log type. Use 'session', 'secrets', or 'world'."
        
    if not os.path.exists(path):
        return f"File not found at {path}"
        
    with open(path, "r") as f:
        return f.read()

def update_world_info(fact: str) -> str:
    """
    Appends a persistent fact to world_info.md.
    Use this for:
    - New NPC names/statuses (e.g. "King Alric is dead").
    - Location details (e.g. "The cave entrance is collapsed").
    - Quest state changes that matter for the whole campaign.
    """
    campaign_dir = CAMPAIGN_ROOT
    path = os.path.join(campaign_dir, "world_info.md")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    entry = f"- [{timestamp}] {fact}\n"
    
    try:
        with open(path, "a") as f:
            f.write(entry)
        return f"Recorded in World Database: {fact}"
    except Exception as e:
        return f"Error updating World Info: {e}"

def summarize_and_compact_session_logic(manual_summary: str = None) -> str:
    """
    Reads the current session log, generates a summary using Gemini (OR uses manual_summary),
    archives the full log, and replaces the main log with the summary.
    """
    session_log, _ = get_log_paths()
    if not os.path.exists(session_log):
        return "Error: Session log not found."
    
    # 1. Read Content
    with open(session_log, "r") as f:
        full_content = f.read()
        
    if len(full_content) < 50:
        return "Log is too short to summarize."

    summary_text = ""
    
    # 2. Determine Summary Source
    if manual_summary:
        # CLIENT-SIDE OVERRIDE
        summary_text = manual_summary
    else:
        # SERVER-SIDE (AUTO) SUMMARIZATION
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                return "Skipped summarization: Feature disabled without GOOGLE_API_KEY. See README.md to set it up."
                
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            You are an expert Dungeon Master assistant.
            Your task is to SUMMARIZE the following D&D Session Log into a processed update for the next session.
            
            PART 1: THE NARRATIVE ("previously on...")
            - Summarize the story, character decisions, and key interactions.
            - Keep it engaging and concise (max 300 words).
            - Omit transient dice rolls (e.g. "Rolled 15 to hit") unless the outcome was critical.
            
            PART 2: STATE TRACKING (Critical!)
            - List the current HP and Status of all characters if known/changed.
            - List any NEW items, loot, or gold acquired.
            - List any Level Ups or XP gained.
            - List active Quest Objectives.
    
            PART 3: HIGHLIGHT REEL (The "Epic Moments")
            - Identify any Critical Hits (Nat 20s) or Fails (Nat 1s) that changed the game.
            - Note any "Clutch" moments where a player saved the day.
            - quote 1-2 memorable lines of dialogue if applicable.
    
            PART 4: WORLD DATABASE UPDATES (Permanent Lore)
            - Identify any NEW permanent facts about the world that should be saved to world_info.md.
            - Examples: NPC names/statuses (dead/alive), location details, alliances.
            - IGNORE temporary states (like "Grog is poisoned").
            - If none, write "None".
            
            FORMAT OUTPUT AS MARKDOWN:
            ## Previously on...
            [Narrative Summary Here]
            
            ## Highlights Reel 🎥
            - **Epic Win**: ...
            - **Epic Fail**: ...
            - **Quote of the Night**: ...
            
            ## Party Status
            - **HP/Conditions**: ...
            - **Inventory Updates**: ...
            - **Quests**: ...
    
            ## World Updates
            - ...
            
            LOG CONTENT:
            {full_content}
            """
            
            response = client.models.generate_content(
                model=os.environ.get("MODEL_NAME", "gemini-1.5-flash"),
                contents=prompt
            )
            
            summary_text = response.text
            if not summary_text:
                return "Error: AI generation failed."
                
        except Exception as e:
            return f"Error during AI summarization: {e}"

    # 3. Extract World Updates for ANY summary source (Manual or Auto)
    if "## World Updates" in summary_text:
        try:
            parts = summary_text.split("## World Updates")
            if len(parts) > 1:
                world_updates = parts[1].strip()
                if world_updates and "None" not in world_updates:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d") # Ensure vars are local or passed
                    update_world_info(f"Auto-Extracted from Session {timestamp}:\n{world_updates}")
        except Exception as e:
            print(f"Failed to auto-update world info: {e}")
     
    # 4. Archive Full Log
 
    # 3. Archive Full Log
    archive_path = session_log.replace(".md", "_full_archive.md")
    with open(archive_path, "w") as f:
        f.write(full_content)
        
    # 4. Write Compact Log
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(session_log, "w") as f:
        f.write(f"# Session Log (Compacted {timestamp})\n\n")
        f.write(f"## Summary\n{summary_text}\n\n")
        f.write(f"*(Full log archived to {os.path.basename(archive_path)})*")
        
    return f"Session compacted! Full log saved to {os.path.basename(archive_path)}. Summary:\n{summary_text}"

# --- Image Generation Logic ---

def get_pending_image_path():
    return os.path.join(CAMPAIGN_ROOT, "pending_image_prompt.txt")

def propose_image(prompt: str) -> str:
    """
    Saves a prompt to the pending file.
    """
    path = get_pending_image_path()
    try:
        with open(path, "w") as f:
            f.write(prompt)
        return f"Image Proposal Saved: '{prompt}'"
    except Exception as e:
        return f"Image Proposal Saved: '{prompt}'"
    except Exception as e:
        return f"Error saving proposal: {e}"

def extract_and_save_prompt_from_text(text: str) -> bool:
    """
    Fallback: Scrapes an image prompt from the model's text output if it forgot to call the tool.
    Looks for: **Image Prompt:** "..."
    """
    import re
    # Match "**Image Prompt:**" and capture until "---", double newline, or end of string.
    # We use DOTALL for the capture group to include internal newlines, but stop at major delimiters.
    patterns = [
        r"\*\*Image Prompt:\*\*\s*(?:\"|”|“)?(.*?)(?:\"|”|“)?\s*(?=---|\[|$)",
        r"Image Prompt:\s*(?:\"|”|“)?(.*?)(?:\"|”|“)?\s*(?=---|\[|$)"
    ]
    
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            prompt = match.group(1).strip()
            # If it captured too much (e.g. whole rest of text), maybe check length
            # But usually --- or [Start of next block] catches it.
            
            if len(prompt) > 10 and len(prompt) < 1000:
                print(f"DEBUG: Scraped prompt: {prompt}")
                propose_image(prompt) 
                return True
            
    return False

def clear_pending_image() -> str:
    """
    Removes the pending prompt file.
    """
    path = get_pending_image_path()
    if os.path.exists(path):
        os.remove(path)
        return "Pending image cleared."
    return "No pending image to clear."

def generate_image_from_pending() -> tuple[bytes, str]:
    """
    Reads pending prompt, calls Imagen, returns (image_bytes, prompt_text).
    Returns (None, error_message) on failure.
    """
    path = get_pending_image_path()
    if not os.path.exists(path):
        return None, "No pending image prompt found."
        
    with open(path, "r") as f:
        prompt = f.read().strip()
        
    if not prompt:
        return None, "Pending prompt was empty."
        
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("DEBUG: Missing Google API Key")
            return None, "Feature disabled: GOOGLE_API_KEY missing. See README.md."
            
        print(f"DEBUG: Generating image for prompt: {prompt[:50]}...")
        client = genai.Client(api_key=api_key)
        
        
        # Use Imagen 4 Fast (Verified in list)
        response = client.models.generate_images(
            model='imagen-4.0-fast-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1
            )
        )
        
        print(f"DEBUG: Response Type: {type(response)}")
        
        if response.generated_images:
            print("DEBUG: Image generated successfully.")
            image_bytes = response.generated_images[0].image.image_bytes
            # Clear pending after successful generation
            os.remove(path)
            return image_bytes, prompt
        else:
            print(f"DEBUG: No images in response. Response: {response}")
            return None, "No images returned from API."
            
    except Exception as e:
        print(f"DEBUG: Exception during generation: {e}")
        return None, f"Generation Error: {e}"

# --- Rule Validation Logic ---

def validate_game_mechanic(action: str, character_name: str) -> str:
    """
    Validates a proposed player action against D&D rules and known character state.
    
    action: "I cast Fireball at level 3" or "I rage and attack"
    character_name: "Grog"
    """
    # 1. Gather Context
    # We need the character's known state (Class, Level, Slots)
    # This comes from the Session Log "Party Status" section.
    session_log, _ = get_log_paths()
    party_status = "Unknown"
    
    if os.path.exists(session_log):
        with open(session_log, "r") as f:
            content = f.read()
            if "## Party Status" in content:
                party_status = content.split("## Party Status")[1].split("##")[0].strip()
            # If we have a compacted log, it might be there. 
            # If not, we might be flying blind, which is fine (permissive).

    # 2. Consult the Rules Sage (Gemini + D&D API)
    # We ask the LLM to perform the logic check using the tools it implicitly knows or we feed it.
    # Actually, to make this robust, we should do a mini-LLM call here only if we want "Ground Truth" 
    # independent of the main bot's context. 
    # BUT, the main bot *is* the one calling this tool. 
    # So the main bot is asking *us* "Is this valid?".
    # We should basically just format the data for the main bot to decide, OR return a strong hint.
    
    # Let's use a quick separate LLM call to be the "Rules Lawyer" so the main bot doesn't hallucinate permission.
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            # OPTIMIZATION: Return the raw data so the Local Agent can decide.
            return f"""VALIDATION DELEGATED TO LOCAL AGENT.
            
            KNOWN STATE:
            {party_status}
            
            INSTRUCTIONS:
            1. Analyze the action "{action}" against the state above.
            2. If you need specific rule text, call `lookup_rule`.
            3. Make the ruling yourself.
            """

        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        You are a D&D Rules Lawyer. Validate this action.
        
        PLAYER: {character_name}
        ACTION: "{action}"
        KNOWN STATUS:
        {party_status}
        
        TASK:
        1. Check if the action is possible for this character based on the status (Level, Class, HP).
        2. Check if the action violates basic 5e rules (e.g. Barbarians casting spells while raging).
        
        OUTPUT:
        - If VALID: Return "VALID".
        - If SUSPICIOUS: Return "WARNING: <reason>".
        - If INVALID: Return "INVALID: <reason>".
        
        Be permissive. If status is missing, assume VALID.
        """
        
        response = client.models.generate_content(
            model=os.environ.get("MODEL_NAME", "gemini-1.5-flash"),
            contents=prompt
        )
        
        return response.text.strip()
        
        return response.text.strip()
        
    except Exception as e:
        return f"Validation Error (Assume Valid): {e}"

# --- Campaign Setup Wizard Logic ---

def get_setup_state_path():
    return os.path.join(CAMPAIGN_ROOT, "setup_state.json")

def get_setup_step() -> int:
    """Returns the current step index (0-4) of the setup wizard."""
    path = get_setup_state_path()
    if not os.path.exists(path):
        return 0 # 0 = Intro/Setting
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("step", 0)
    except:
        return 0

def advance_setup_step() -> str:
    """Increments the setup step."""
    path = get_setup_state_path()
    current = get_setup_step()
    next_step = current + 1
    
    with open(path, "w") as f:
        json.dump({"step": next_step, "updated": datetime.datetime.now().isoformat()}, f)
    
    return f"Setup advanced to Step {next_step}."

def get_setup_instructions(step: int) -> str:
    """Returns the System Prompt injection for the current setup step."""
    if step == 0:
        return """
        [SETUP MODE: STEP 1 of 4 - INTRO & SETTING]
        Your Goal: Introduce yourself and establish the Campaign Setting.
        1. Tell the players you are monitoring chat but will only respond when tagged.
        2. Ask them to discuss what type of campaign they want (High Fantasy, Sci-Fi, Horror, etc.).
        3. Explain they should Chat amongst themselves, then tag you (@DeeSim) with the final decision.
        4. CRITICAL: DO NOT call `complete_setup_step()` until the players have explicitly agreed on a setting.
        5. If they are still discussing, just acknowledge and wait.
        6. IMPROVE THE EXPERIENCE: If the answer is vague, ask clarifying questions (e.g. "Grimdark or Noblebright?").
        7. ONLY when you have a clear, final answer, CALL `complete_setup_step()`.
        """
    elif step == 1:
        return """
        [SETUP MODE: STEP 2 of 4 - ROSTER]
        Your Goal: Confirm the Player Roster.
        1. Ask one player to tag all participants (including themselves) so you know who is playing.
        2. Remind them this isn't fixed; players can join/leave later.
        3. Players should use command `!iam <Name>` to register if they haven't.
        4. CRITICAL: DO NOT advance until you have at least one confirmed player.
        5. Ask: "Is that everyone for now?" before proceeding.
        6. When the roster is confirmed by a player, CALL `complete_setup_step()`.
        """
    elif step == 2:
        return """
        [SETUP MODE: STEP 3 of 4 - CHARACTER SHEEETS]
        Your Goal: Collect Character Data.
        1. Ask EACH player to provide their: Class, Level, Name, Race, Background, and Stats (STR/DEX/etc).
        2. Request a brief backstory or playstyle preference.
        3. YOU MUST call `submit_character_sheet(name, details)` for EACH player as they provide data.
        4. Do NOT call `complete_setup_step()` after just one player if others are present.
        5. Ask: "Has everyone submitted their details?"
        6. If a player wants to skip providing details now, that is okay, but confirm explicitly.
        7. When all active players are accounted for, CALL `complete_setup_step()`.
        """
    elif step == 3:
        return """
        [SETUP MODE: STEP 4 of 4 - DICE PREFERENCE]
        Your Goal: Establish Dice Rolling Etiquette.
        1. Ask if they prefer to roll real physical dice (Trust System) or if they want YOU (the Bot) to roll for them.
        2. Explain that for the Trust System, you will tell them the DC and consequence, and they report the result.
        3. Note their preference.
        4. CRITICAL: Confirm the choice before finishing.
        5. CALL `complete_setup_step()` to finish setup and start the game!
        """
    else:
        return "" # Setup complete, normal play.

def save_character_sheet(name: str, details_text: str) -> str:
    """
    Saves unstructured character details to a file for reference.
    """
    sheets_dir = os.path.join(CAMPAIGN_ROOT, "character_sheets")
    os.makedirs(sheets_dir, exist_ok=True)
    
    safe_name = "".join(x for x in name if x.isalnum() or x in (' ', '_', '-')).strip()
    path = os.path.join(sheets_dir, f"{safe_name}.txt")
    
    with open(path, "w") as f:
        f.write(f"Character Sheet: {name}\n")
        f.write(f"Recorded: {datetime.datetime.now().isoformat()}\n")
        f.write("-------------------------------------------\n")
        f.write(details_text)
        
    
    with open(path, "w") as f:
        f.write(f"Character Sheet: {name}\n")
        f.write(f"Recorded: {datetime.datetime.now().isoformat()}\n")
        f.write("-------------------------------------------\n")
        f.write(details_text)
        
    return f"Saved character sheet for {name}."

# --- Name Generation Logic ---

def generate_random_name(race: str = "any", gender: str = "any") -> str:
    """
    Generates a random fantasy name using the 'fantasynames' library.
    race: 'elf', 'dwarf', 'human', 'hobbit', 'place', or 'any'.
    """
    try:
        # Place Name Logic (Hack: Use surnames)
        if race.lower() in ["place", "town", "city", "location"]:
            # Human and Anglo names often have town-like suffixes (-ton, -ford, -bury)
            full_name = fn.human() if random.random() < 0.5 else fn.anglo()
            if " " in full_name:
                return full_name.split(" ")[-1] # Return surname (e.g. "Kirkbury")
            return full_name
            
        # Character Name Logic
        if race.lower() == "elf":
            return fn.elf()
        elif race.lower() == "dwarf":
            return fn.dwarf()
        elif race.lower() == "human":
            return fn.human()
        elif race.lower() == "hobbit":
            return fn.hobbit()
        elif race.lower() == "anglo":
            return fn.anglo()
        elif race.lower() == "french":
            return fn.french()
        else:
            # For Orcs, Goblins, Gnomes, etc. we return None 
            # to signal the bot to generate it via LLM
            return None
    except Exception as e:
        return f"NameError: {e}"
