import sqlite3
import os
import contextlib
from core.campaign import get_campaign_root

def get_db_path() -> str:
    """Returns the path to the SQLite database for the active campaign."""
    root = get_campaign_root()
    return os.path.join(root, "campaign_state.db")

@contextlib.contextmanager
def get_db_connection():
    """Context manager for SQLite database connections."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # Enable accessing columns by name
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initializes the database schema if tables don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Players Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                slack_id TEXT PRIMARY KEY,
                character_name TEXT NOT NULL,
                race TEXT,
                class TEXT,
                level INTEGER DEFAULT 1,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Character Sheets Table (Unstructured text like stats/backstory)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_sheets (
                character_name TEXT PRIMARY KEY,
                details_text TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inventory Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                weight REAL DEFAULT 0.0,
                FOREIGN KEY (character_id) REFERENCES players (slack_id)
            )
        ''')
        
        # Quests Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Chat History & Context (Handled by ChromaDB / Vector Store)
        # We are intentionally leaving chat logs out of SQLite to enable semantic search capabilities
        pass

