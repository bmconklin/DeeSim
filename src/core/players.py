from core.database import get_db_connection

# --- Player & Attendance Logic ---

def register_player(user_id: str, char_name: str) -> str:
    """Registers or updates a player in the SQLite database."""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO players (slack_id, character_name) 
            VALUES (?, ?)
            ON CONFLICT(slack_id) DO UPDATE SET character_name=excluded.character_name
        ''', (user_id, char_name))
    return f"Registered <@{user_id}> as **{char_name}**."

def get_character_name(user_id: str) -> str:
    """Retrieves a character name by Slack ID."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT character_name FROM players WHERE slack_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row['character_name']
    return "Unknown Hero"

def get_user_id_by_character_name(char_name: str) -> str | None:
    """
    Reverse lookup: Find Slack User ID from Character Name.
    Case-insensitive partial match via SQLite LIKE.
    """
    with get_db_connection() as conn:
        # Try exact match first
        cursor = conn.execute("SELECT slack_id FROM players WHERE LOWER(character_name) = LOWER(?)", (char_name.strip(),))
        row = cursor.fetchone()
        if row:
            return row['slack_id']
            
        # Try partial match
        like_query = f"%{char_name.strip()}%"
        cursor = conn.execute("SELECT slack_id FROM players WHERE character_name LIKE ?", (like_query,))
        row = cursor.fetchone()
        if row:
            return row['slack_id']
            
    return None
