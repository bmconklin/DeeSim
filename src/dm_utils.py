import os
import random
import requests
import json
import datetime
import re
from google.genai import types
from google import genai
try:
    import fantasynames as fn
except ImportError:
    fn = None

from core.campaign import (
    get_campaign_root,
    get_current_session_dir
)

# --- Deep Memory Logic ---
from core.state_manager import (
    log_to_file
)
from core.players import get_user_id_by_character_name
from core.database import get_db_connection



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








def get_log_paths():
    session_dir = get_current_session_dir()
    session_log = os.path.join(session_dir, "session_log.md")
    secrets_log = os.path.join(session_dir, "secrets_log.md")
    return session_log, secrets_log

def start_new_session_logic(summary_of_previous: str) -> str:
    root = get_campaign_root()
    current_session_file = os.path.join(root, "current_session.txt")
    if not os.path.exists(current_session_file):
        return "Error: Could not find current_session.txt. Is this a valid campaign?"
        
    with open(current_session_file, "r") as f:
        current_name = f.read().strip()
        
    try:
        current_num = int(current_name.split("_")[1])
    except Exception:
        current_num = 0
        
    next_num = current_num + 1
    next_session_name = f"session_{next_num}"
    next_session_dir = os.path.join(root, next_session_name)
    
    os.makedirs(next_session_dir, exist_ok=True)
    
    with open(os.path.join(next_session_dir, "session_log.md"), "w") as f:
        f.write(f"# Session Log: {next_session_name}\n\n")
        f.write(f"## Previously on...\n{summary_of_previous}\n\n")
        
    with open(os.path.join(next_session_dir, "secrets_log.md"), "w") as f:
        f.write(f"# DM Secrets: {next_session_name}\n\n")
        
    with open(current_session_file, "w") as f:
        f.write(next_session_name)
        
    return f"Successfully started the next chapter: **{next_session_name}**. The stage is set!"

def request_player_roll_logic(check_type: str, dc: int, consequence: str) -> str:
    session_log, secrets_log = get_log_paths()
    log_message = f"**WAITING FOR PLAYER** | Type: {check_type} | DC: {dc} | Fail Consequence: {consequence}"
    log_to_file(secrets_log, log_message)
    return "Logged DC and Consequence. You may now ask the player to roll."



def read_campaign_log(log_type: str) -> str:
    """
    Reads the full content of a specified log file.
    log_type: 'session', 'secrets', or 'world'.
    """
    session_log, secrets_log = get_log_paths()
    campaign_dir = get_campaign_root()
    
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

def list_sessions() -> str:
    """
    Lists all session directories in the active campaign with metadata.
    Shows which files exist in each session and which session is current.
    """
    root = get_campaign_root()
    current_session_file = os.path.join(root, "current_session.txt")
    current_name = ""
    if os.path.exists(current_session_file):
        with open(current_session_file, "r") as f:
            current_name = f.read().strip()

    sessions = []
    for entry in sorted(os.listdir(root)):
        session_dir = os.path.join(root, entry)
        if os.path.isdir(session_dir) and entry.startswith("session_"):
            files = os.listdir(session_dir)
            has_log = "session_log.md" in files
            has_secrets = "secrets_log.md" in files
            has_archive = "session_log_full_archive.md" in files
            is_current = (entry == current_name)

            marker = " (CURRENT)" if is_current else ""
            file_list = []
            if has_log:
                file_list.append("session_log")
            if has_secrets:
                file_list.append("secrets_log")
            if has_archive:
                file_list.append("full_archive")
            sessions.append(f"- {entry}{marker}: [{', '.join(file_list)}]")

    if not sessions:
        return "No sessions found."

    return "Sessions:\n" + "\n".join(sessions)

def read_session(session_name: str = "current") -> str:
    """
    Reads all log files from a specific session directory.
    Returns combined content from session_log.md, secrets_log.md,
    and session_log_full_archive.md with clear section headers.

    Args:
        session_name: e.g. "session_3" or "current" for the active session.
    """
    root = get_campaign_root()

    if session_name == "current":
        current_session_file = os.path.join(root, "current_session.txt")
        if os.path.exists(current_session_file):
            with open(current_session_file, "r") as f:
                session_name = f.read().strip()
        else:
            return "Error: Could not determine current session."

    session_dir = os.path.join(root, session_name)
    if not os.path.isdir(session_dir):
        available = list_sessions()
        return f"Session '{session_name}' not found.\n{available}"

    sections = []
    sections.append(f"# Full Recap: {session_name}\n")

    # Session log (compacted summary or active log)
    session_log_path = os.path.join(session_dir, "session_log.md")
    if os.path.exists(session_log_path):
        with open(session_log_path, "r") as f:
            content = f.read().strip()
        sections.append(f"## Session Log\n{content}\n")

    # Full archive (raw chronological log before compacting)
    archive_path = os.path.join(session_dir, "session_log_full_archive.md")
    if os.path.exists(archive_path):
        with open(archive_path, "r") as f:
            content = f.read().strip()
        sections.append(f"## Full Archive\n{content}\n")

    # Secrets log (DM-only information)
    secrets_path = os.path.join(session_dir, "secrets_log.md")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            content = f.read().strip()
        sections.append(f"## DM Secrets\n{content}\n")

    if len(sections) == 1:
        return f"Session '{session_name}' exists but contains no log files."

    return "\n".join(sections)

def update_world_info(fact: str) -> str:
    """
    Appends a persistent fact to world_info.md.
    Use this for:
    - New NPC names/statuses (e.g. "King Alric is dead").
    - Location details (e.g. "The cave entrance is collapsed").
    - Quest state changes that matter for the whole campaign.
    """
    campaign_dir = get_campaign_root()
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
    return os.path.join(get_campaign_root(), "pending_image_prompt.txt")

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
        return f"Error saving proposal: {e}"

def clear_pending_image() -> str:
    """Removes the pending image prompt."""
    path = get_pending_image_path()
    if os.path.exists(path):
        os.remove(path)
        return "Cleared pending image prompt."
    return "No pending image prompt to clear."

def extract_and_save_prompt_from_text(text: str) -> bool:
    """
    Fallback: Scrapes an image prompt from the model's text output if it forgot to call the tool.
    Looks for: **Image Prompt:** "..."
    """
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

def save_image_to_campaign(image_bytes: bytes, prompt: str) -> str:
    """
    Saves image bytes to the visuals/ folder in the current session.
    """
    session_dir = get_current_session_dir()
    visuals_dir = os.path.join(session_dir, "visuals")
    os.makedirs(visuals_dir, exist_ok=True)
    
    # Create safe filename
    safe_name = re.sub(r"[^a-zA-Z0-9 ]", "", prompt[:30]).strip().replace(" ", "_")
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{safe_name}.png"
    filepath = os.path.join(visuals_dir, filename)
    
    try:
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filepath
    except Exception as e:
        print(f"DEBUG: Failed to save image to campaign: {e}")
        return None

def generate_image_from_pending() -> tuple[str, str]:
    """
    Reads pending prompt, calls Imagen, saves result to campaign, 
    returns (saved_filepath, prompt_text).
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
            
            # Save to campaign folder if possible
            saved_path = save_image_to_campaign(image_bytes, prompt)
            
            # Clear pending after successful generation
            os.remove(path)
            
            if saved_path:
                return saved_path, prompt
            else:
                return "SUCCESS_BUT_SAVE_FAILED", prompt
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
    return os.path.join(get_campaign_root(), "setup_state.json")

def get_setup_step() -> int:
    """Returns the current step index (0-4) of the setup wizard."""
    path = get_setup_state_path()
    if not os.path.exists(path):
        return 0 # 0 = Intro/Setting
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("step", 0)
    except Exception:
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
        5. STARTING LOCATION: Once a setting is picked, you must determine the starting location. 
           USE THE TOOL: `generate_name(race='place', count=10)` to get a large pool of options.
           DECISION: Evaluate the results, select the name that best fits the theme (e.g., 'Winterfell' for a cold setting), and announce it as the final starting location.
        6. If they are still discussing the setting, just acknowledge and wait.
        7. IMPROVE THE EXPERIENCE: If the answer is vague, ask clarifying questions (e.g. "Grimdark or Noblebright?").
        8. ONLY when you have a clear setting AND you have declared the starting location, CALL `complete_setup_step()`.
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
    Saves unstructured character details to the database for reference.
    """
    from core.database import get_db_connection
    safe_name = name.strip()
    
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO character_sheets (character_name, details_text) 
            VALUES (?, ?) 
            ON CONFLICT(character_name) DO UPDATE SET 
            details_text=excluded.details_text, 
            updated_at=CURRENT_TIMESTAMP
        ''', (safe_name, details_text))
            
    return f"Saved character sheet for {safe_name}."

def list_character_sheets() -> str:
    """
    Returns a list of all saved character sheet names for the active campaign.
    """
    from core.database import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT character_name FROM character_sheets ORDER BY character_name")
        rows = cursor.fetchall()
        
    if not rows:
        return "No character sheets found."
        
    names = [row["character_name"] for row in rows]
    return "Characters:\n" + "\n".join(f"- {n}" for n in names)

def read_character_sheet(name: str) -> str:
    """
    Reads and returns the full contents of a specific character's sheet.
    """
    from core.database import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT details_text, updated_at FROM character_sheets WHERE character_name = ?", (name.strip(),))
        row = cursor.fetchone()
        
    if not row:
        available = list_character_sheets()
        return f"No character sheet found for '{name}'.\n{available}"
        
    return f"Character Sheet: {name.strip()}\nLast Updated: {row['updated_at']}\n-------------------------------------------\n{row['details_text']}"

    # Dead code below - skipping for safety

# --- Name Generation Logic ---

def generate_random_name(race: str = "any", count: int = 1) -> str:
    """
    Generates random fantasy names.
    race: 'elf', 'dwarf', 'human', 'hobbit', 'place' (towns), or 'any'.
    count: How many names to generate.
    """
    try:
        names = []
        for _ in range(max(1, min(count, 10))):
            name = None
            r = race.lower()

            if r in ["place", "town", "city", "location", "village"]:
                # Place names use local generation (no fantasynames needed)
                roots = [
                    "Oak", "Deep", "Shadow", "Gold", "High", "Stone", "River", "Green", "Winter", "Summer",
                    "Iron", "Black", "White", "Gray", "Storm", "Cloud", "Sun", "Moon", "Star", "Fire",
                    "Frost", "Mist", "Raven", "Wolf", "Dragon", "Amber", "Silver", "Night", "Dawn"
                ]
                suffixes = [
                    "haven", "fell", "wood", "run", "crest", "ford", "bury", "ton", "field", "bridge",
                    "glen", "peak", "hold", "spire", "watch", "keep", "gate", "port", "marsh", "vale",
                    "dale", "ridge", "point", "well", "drift", "bay", "rock", "cliff"
                ]
                name = f"{random.choice(roots)}{random.choice(suffixes)}"
            elif fn is None:
                # fantasynames unavailable (e.g. Python 3.13+); signal LLM to generate
                return None
            elif r == "elf":
                name = fn.elf()
            elif r == "dwarf":
                name = fn.dwarf()
            elif r == "human":
                name = fn.human()
            elif r == "hobbit":
                name = fn.hobbit()
            elif r == "anglo":
                name = fn.anglo()
            else:
                # Default to a mix
                pick = random.choice([fn.human, fn.elf, fn.dwarf, fn.anglo])
                name = pick()

            if name:
                names.append(name)

        if not names:
            return None

        if len(names) == 1:
            return names[0]
        return ", ".join(names)

    except Exception:
        return None

def update_combat_state(entities: list) -> str:
    """
    Writes or updates the '## Active Combat' section in secrets_log.md.
    entities: List of dicts, e.g. [{"name": "Goblin 1", "hp": 7, "max_hp": 7, "ac": 15, "notes": ""}]
    """
    _, secrets_log = get_log_paths()
    
    # Read existing content
    content = ""
    if os.path.exists(secrets_log):
        with open(secrets_log, "r") as f:
            content = f.read()
            
    # Prepare combat table
    header = "## Active Combat\n\n| Name | HP | AC | Notes |\n| :--- | :--- | :--- | :--- |\n"
    rows = ""
    for e in entities:
        hp_str = f"{e.get('hp', 0)}/{e.get('max_hp', 0)}"
        rows += f"| {e.get('name', 'Unknown')} | {hp_str} | {e.get('ac', 0)} | {e.get('notes', '')} |\n"
    
    new_combat_section = header + rows + "\n"
    
    if "## Active Combat" in content:
        # Replace existing section
        import re
        # Find everything from ## Active Combat to the next ## or end of file
        pattern = r"## Active Combat\n.*?(?=\n##|$)"
        updated_content = re.sub(pattern, new_combat_section.strip(), content, flags=re.DOTALL)
    else:
        # Append to end
        updated_content = content.strip() + "\n\n" + new_combat_section
        
    with open(secrets_log, "w") as f:
        f.write(updated_content.strip() + "\n")
        
    return "Combat state updated in secrets_log.md."

def get_combat_state() -> str:
    """
    Retrieves the '## Active Combat' section from secrets_log.md.
    """
    _, secrets_log = get_log_paths()
    if not os.path.exists(secrets_log):
        return "No combat state found (secrets_log.md missing)."
        
    with open(secrets_log, "r") as f:
        content = f.read()
        
    if "## Active Combat" not in content:
        return "No active combat section found."
        
    pattern = r"## Active Combat\n.*?(?=\n##|$)"
    match = re.search(pattern, content, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
        
    return "Failed to parse combat state."

    return "Failed to parse combat state."

def manage_inventory(action: str, item_name: str = "", quantity: int = 1, weight: float = 0.0, character_name: str = None) -> str:
    """
    Manages character inventory using SQLite.
    Args:
        action: "add", "remove", "check", "list", "search".
        item_name: Name of the item.
        quantity: Amount to add/remove.
        weight: Weight per unit (optional).
        character_name: Who owns the item.
    """
    # --- Global Search Actions (No Character Required) ---
    if action == "search":
        item_key = item_name.strip()
        if not item_key:
            return "Error: item_name required for search."
            
        with get_db_connection() as conn:
            query = f"%{item_key}%"
            cursor = conn.execute('''
                SELECT p.character_name, i.item_name, i.quantity 
                FROM inventory i
                JOIN players p ON i.character_id = p.slack_id
                WHERE i.item_name LIKE ?
            ''', (query,))
            rows = cursor.fetchall()
            
            if not rows:
                return f"No items found matching '{item_name}' in any inventory."
                
            found = [f"- **{row['character_name']}**: {row['quantity']}x {row['item_name']}" for row in rows]
            return "\n".join(["### 🔍 Item Search Results"] + found)

    # --- Character Specific Actions ---
    if not character_name:
        return "Error: Character name required."
    
    # Resolve character to slack_id
    slack_id = get_user_id_by_character_name(character_name)
    
    if not slack_id:
         # Auto-register if missing (graceful fallback)
         from core.players import register_player
         # Create a fake temporary ID for them since they don't have a slack account attached yet
         import uuid
         slack_id = f"npc_{str(uuid.uuid4())[:8]}"
         register_player(slack_id, character_name)
    
    item_key = item_name.strip()
    
    with get_db_connection() as conn:
        if action == "add":
            cursor = conn.execute("SELECT quantity FROM inventory WHERE character_id = ? AND item_name = ?", (slack_id, item_key))
            row = cursor.fetchone()
            
            if row:
                new_qty = row['quantity'] + quantity
                conn.execute(
                    "UPDATE inventory SET quantity = ?, weight = ? WHERE character_id = ? AND item_name = ?",
                    (new_qty, weight, slack_id, item_key)
                )
            else:
                conn.execute(
                    "INSERT INTO inventory (character_id, item_name, quantity, weight) VALUES (?, ?, ?, ?)",
                    (slack_id, item_key, quantity, weight)
                )
            return f"Added {quantity}x {item_name} to {character_name}'s inventory."
            
        elif action == "remove":
            cursor = conn.execute("SELECT quantity FROM inventory WHERE character_id = ? AND item_name = ?", (slack_id, item_key))
            row = cursor.fetchone()
            
            if not row:
                return f"{character_name} does not have {item_name}."
                
            current_qty = row['quantity']
            if quantity >= current_qty:
                conn.execute("DELETE FROM inventory WHERE character_id = ? AND item_name = ?", (slack_id, item_key))
                return f"Removed all {item_name} from {character_name}."
            else:
                new_qty = current_qty - quantity
                conn.execute("UPDATE inventory SET quantity = ? WHERE character_id = ? AND item_name = ?", (new_qty, slack_id, item_key))
                return f"Removed {quantity}x {item_name} from {character_name}. Remaining: {new_qty}."
                
        elif action == "check":
            cursor = conn.execute("SELECT quantity, weight FROM inventory WHERE character_id = ? AND item_name = ?", (slack_id, item_key))
            row = cursor.fetchone()
            if row:
                total_w = row['weight'] * row['quantity']
                return f"{character_name} has {row['quantity']}x {item_name} (Weight: {total_w:.1f})."
            else:
                return f"{character_name} does not have {item_name}."
                
        elif action == "list":
            cursor = conn.execute("SELECT item_name, quantity, weight FROM inventory WHERE character_id = ?", (slack_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return f"{character_name}'s inventory is empty."
                
            lines = [f"**{character_name}'s Inventory:**"]
            total_weight = 0.0
            
            for row in rows:
                qty = row["quantity"]
                wt = row["weight"] * qty
                total_weight += wt
                lines.append(f"- {qty}x {row['item_name']} ({wt:.1f} lbs)")
                
            lines.append(f"**Total Weight:** {total_weight:.1f} lbs")
            return "\n".join(lines)
            
        else:
            return f"Unknown action: {action}"

def lookup_item_details(item_name: str) -> str:
    """
    Looks up an item in the D&D API to find its rarity, cost, and type.
    """
    import dnd_bridge
    
    # 1. Search for the item
    results = dnd_bridge.search_dnd_rules(item_name)
    
    if "error" in results:
        return f"Error looking up item: {results['error']}"
        
    # Check top results across categories
    top = results.get("top_results", [])
    if not top:
        return f"No items found matching '{item_name}'."
        
    # Find the best ITEM match (equipment or magic-items)
    best_item = None
    
    # Priority 1: Check top results for equipment/magic-items
    for match in top:
        cat = match.get("category")
        if cat in ["equipment", "magic-items"]:
            # We need the full details which are in the 'results' dict, not just the top_results summary
            # But wait, search_all_categories returns 'results' indexed by category
            # Let's look there using the index from top_results
            target_index = match.get("index")
            try:
                items_in_cat = results["results"][cat]["items"]
                for i in items_in_cat:
                    if i["index"] == target_index:
                        best_item = i
                        best_item["category"] = cat
                        best_item["category"] = cat
                        break
            except Exception:
                continue
        if best_item:
            break
            
    # Priority 2: If no top result is an item, scan the full results for ANY item
    if not best_item:
        for cat in ["magic-items", "equipment"]:
            if cat in results.get("results", {}):
                items = results["results"][cat].get("items", [])
                if items:
                    best_item = items[0]
                    best_item["category"] = cat
                    break
                    
    if not best_item:
        return f"No equipment or magic items found for '{item_name}'."
        
    # 3. Extract Details
    details = best_item.get("details", {})
    name = best_item.get("name")
    
    # Rarity
    rarity = "Unknown"
    if "rarity" in details:
        rarity = details["rarity"].get("name", "Unknown")
        
    # Type / Subcategory
    item_type = "Item"
    if "equipment_category" in details:
        item_type = details["equipment_category"].get("name", "Equipment")
    if "card_type" in details: # Just in case
        item_type = details["card_type"]
        
    # Cost (for Equipment)
    cost_str = "N/A"
    if "cost" in details:
        cost_str = f"{details['cost']['quantity']} {details['cost']['unit']}"
        
    # Description (Snippet)
    desc = "No description."
    if "desc" in details:
        if isinstance(details["desc"], list):
            desc = " ".join(details["desc"])
        else:
            desc = str(details["desc"])
    
    # Formatted Output
    return f"""**{name}**
- **Type**: {item_type}
- **Rarity**: {rarity}
- **Cost**: {cost_str}
- **Description**: {desc[:200]}..."""

def manage_quests(action: str, title: str = "", description: str = None, status: str = None) -> str:
    """
    Manages campaign quests using SQLite.
    Args:
        action: "add", "update", "complete", "list".
        title: Quest title (required for add/update/complete).
        description: Quest objective or update notes.
        status: "Active", "Completed", "Failed" (for update).
    """
    if action == "list":
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT title, description, status FROM quests")
            rows = cursor.fetchall()
            
            if not rows:
                return "No quests found."
                
            active = []
            completed = []
            for row in rows:
                line = f"- **{row['title']}**: {row['description']} ({row['status']})"
                if row['status'] == 'Active':
                    active.append(line)
                else:
                    completed.append(line)
                    
            output = []
            if active:
                output.append("### 🛡️ Active Quests")
                output.extend(active)
            if completed:
                output.append("\n### ✅ Completed Quests")
                output.extend(completed)
                
            return "\n".join(output)

    # For modifiers, title is required
    if not title:
        return "Error: Quest title required."
        
    title_key = title.strip()
    
    with get_db_connection() as conn:
        if action == "add":
            cursor = conn.execute("SELECT id FROM quests WHERE title = ?", (title_key,))
            if cursor.fetchone():
                return f"Quest '{title}' already exists."
                
            conn.execute(
                "INSERT INTO quests (title, description, status) VALUES (?, ?, ?)",
                (title_key, description or "No description", "Active")
            )
            return f"Quest added: {title}"
            
        elif action == "update":
            cursor = conn.execute("SELECT description, status FROM quests WHERE title = ?", (title_key,))
            row = cursor.fetchone()
            if not row:
                return f"Quest '{title}' not found."
                
            new_desc = description if description is not None else row['description']
            new_status = status if status is not None else row['status']
            
            conn.execute(
                "UPDATE quests SET description = ?, status = ? WHERE title = ?",
                (new_desc, new_status, title_key)
            )
            return f"Quest updated: {title}"
            
        elif action == "complete":
            cursor = conn.execute("SELECT id FROM quests WHERE title = ?", (title_key,))
            if not cursor.fetchone():
                return f"Quest '{title}' not found."
                
            conn.execute("UPDATE quests SET status = 'Completed' WHERE title = ?", (title_key,))
            return f"Quest completed: {title}"
            
        else:
            return f"Unknown action: {action}"

def lookup_monster(monster_name: str) -> str:
    """
    Looks up a monster's stats for combat.
    """
    import dnd_bridge
    
    # 1. Search for the monster
    results = dnd_bridge.search_dnd_rules(monster_name)
    
    if "error" in results:
        return f"Error looking up monster: {results['error']}"
        
    # Check top results
    top = results.get("top_results", [])
    if not top:
        return f"No monsters found matching '{monster_name}'."
        
    best_match = None
    
    # Priority 1: Check top results for monsters
    for match in top:
        if match.get("category") == "monsters":
            target_index = match.get("index")
            try:
                items_in_cat = results["results"]["monsters"]["items"]
                for i in items_in_cat:
                    if i["index"] == target_index:
                        best_match = i
                        break
                        best_match = i
                        break
            except Exception:
                continue
        if best_match:
            break
    if not best_match:
        # Priority 2: Scan full results
        if "monsters" in results.get("results", {}):
            items = results["results"]["monsters"].get("items", [])
            if items:
                best_match = items[0]
                 
    if not best_match:
        return f"No monster stats found for '{monster_name}'."

    # Extract Stats
    details = best_match.get("details", {})
    name = best_match.get("name")
    
    size = details.get("size", "Medium")
    type_ = details.get("type", "Unknown")
    ac = 10
    if "armor_class" in details:
        ac_data = details["armor_class"]
        if isinstance(ac_data, list) and ac_data:
            ac = ac_data[0].get("value", 10)
            
    hp = details.get("hit_points", 0)
    hit_dice = details.get("hit_dice", "1d8")
    
    speed = "30 ft."
    if "speed" in details:
        speed_str = []
        for k, v in details["speed"].items():
            speed_str.append(f"{k}: {v}")
        speed = ", ".join(speed_str)
        
    # Actions
    actions = []
    if "actions" in details:
        for act in details["actions"]:
            act_name = act.get("name", "Unknown")
            desc = act.get("desc", "")
            actions.append(f"- **{act_name}**: {desc[:150]}...")
            
    # Format
    return f"""**{name}**
- **Size/Type**: {size} {type_}
- **AC**: {ac} | **HP**: {hp} ({hit_dice})
- **Speed**: {speed}
- **Actions**:
{chr(10).join(actions[:3])}
..."""


def load_skills_content() -> str:
    """
    Scans the skills/ directory for SKILL.md files and formats them for the prompt.
    """
    # Assuming skills/ is at the project root, not campaign root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills_dir = os.path.join(project_root, "skills")
    
    if not os.path.exists(skills_dir):
        return ""
        
    skill_content = "\n\n## Specialized Skills\nYou have access to the following specialized workflows. Use them when applicable:\n"
    
    # Simple walk
    count = 0
    for root_dir, dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files:
            try:
                path = os.path.join(root_dir, "SKILL.md")
                with open(path, "r") as f:
                    content = f.read()
                    # Clean up frontmatter if present (between ---)
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            content = parts[2].strip()
                            
                    folder_name = os.path.basename(root_dir)
                    skill_content += f"\n### Skill: {folder_name.replace('_', ' ').title()}\n{content}\n"
                    count += 1
            except Exception as e:
                print(f"Error loading skill {path}: {e}")
                
    if count == 0:
        return ""
        
    return skill_content

def get_system_instruction():
    session_dir = get_current_session_dir()
    # Check session dir first, then campaign root
    prompt_path = os.path.join(session_dir, "system_prompt.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(get_campaign_root(), "system_prompt.txt")
        
    base_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            base_prompt = f.read()
    else:
        base_prompt = "You are a Dungeon Master. Use the tools provided to run the game."

    naming_rules = """---
## Universal Naming Principles
When generating names for NPCs, locations, items, or anything else:
1. ALWAYS use the `generate_name` tool with a `count` of 5-10.
2. Review the resulting list of names and evaluate them against the current theme and tone of the campaign.
3. Make the final executive decision as the DM. Select the best fit and announce it firmly.
4. Do not present options to the players unless specifically asked to brainstorm with them; you should stay in character as the authoritative world-builder.

## Combat Management Rules
To ensure mechanical consistency and prevent narration hallucinations:
1. **Initialize Combat**: When a battle begins, ALWAYS use `initialize_combat` to set up the enemies (Name, HP, AC, Notes). Generate their stats based on official 5e rules if not provided.
2. **Track Every Hit**: Every time a creature takes damage, heals, or uses a limited resource (like a spell slot), use `track_combat_change`.
3. **Verify Before Narrating**: Before you describe an enemy dying or being wounded, check their current state using `read_campaign_log(log_type='secrets')`.
4. **Secret Tracking**: All combat stats are stored in `secrets_log.md`. DO NOT reveal exact HP numbers to players unless they have a specific ability to see them; use descriptive terms like "bloodied" (half HP) or "near death".
---
"""
    skills_section = load_skills_content()
    
    return base_prompt + naming_rules + skills_section + """
## Deep Memory & History
Your memory is not limited to the active session. The entire campaign history is available to you.
1. **Always Check History**: If a user asks about a past event (e.g., "Who did I fight in Session 1?"), and it is not in your current summary, DO NOT say "I don't know" or "That log isn't loaded."
2. **Use the Tool**: Call `lookup_past_session(query="...")` immediately to find the answer.
3. **Deep Dive**: If the summary is insufficient, look up the specific session using `lookup_past_session(query="IGNORED", session_name="session_X")` to read the full transcript.
4. **Be Authoritative**: Once you retrieve the info, treat it as something you always knew.
"""
