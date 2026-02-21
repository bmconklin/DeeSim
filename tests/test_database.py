import os
import pytest
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

import contextlib
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="function")
def mock_get_db_connection():
    """Creates a temp DB, initializes it, and patches get_db_path so all DB ops use it."""
    from core.database import init_db
    
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    
    # Patch get_db_path globally for this test
    with patch("core.database.get_db_path", return_value=path):
        init_db()  # Creates tables using the real code against the temp file
        yield path # Tests run here, picking up the patched path
        
    os.close(fd)
    os.remove(path)

# --- TESTS ---

def test_player_registration(mock_get_db_connection):
    from core.players import register_player, get_character_name, get_user_id_by_character_name
    
    # Test registration
    res = register_player("U123", "Grog Strongjaw")
    assert "Registered" in res
    
    # Test lookup by ID
    name = get_character_name("U123")
    assert name == "Grog Strongjaw"
    
    # Test lookup by character name (exact & partial)
    assert get_user_id_by_character_name("Grog Strongjaw") == "U123"
    assert get_user_id_by_character_name("grog") == "U123"

def test_quest_management(mock_get_db_connection):
    from dm_utils import manage_quests
    
    # Add quest
    res = manage_quests("add", title="Slay the Dragon", description="Defeat the red dragon in the volcano.")
    assert "added" in res
    
    # List active quest
    res = manage_quests("list")
    assert "Slay the Dragon" in res
    assert "Active" in res
    
    # Update quest
    res = manage_quests("update", title="Slay the Dragon", description="Defeat the ancient red dragon.")
    assert "updated" in res
    
    # Complete quest
    res = manage_quests("complete", title="Slay the Dragon")
    assert "completed" in res
    
    # List completed
    res = manage_quests("list")
    assert "Completed Quests" in res

def test_inventory_management(mock_get_db_connection):
    from dm_utils import manage_inventory
    from core.players import register_player
    
    # Setup player for FK constraint
    register_player("U999", "Vax")
    
    # Add item
    res = manage_inventory("add", item_name="Dagger", quantity=2, weight=1.0, character_name="Vax")
    assert "Added 2x Dagger" in res
    
    # Check item
    res = manage_inventory("check", item_name="Dagger", character_name="Vax")
    assert "has 2x Dagger" in res
    
    # List inventory
    res = manage_inventory("list", item_name="", character_name="Vax")
    assert "2x Dagger" in res
    assert "2.0 lbs" in res
    
    # Search globally
    res = manage_inventory("search", item_name="Dagger")
    assert "Vax" in res
    
    # Remove partial
    res = manage_inventory("remove", item_name="Dagger", quantity=1, character_name="Vax")
    assert "Remaining: 1" in res
    
    # Remove all
    res = manage_inventory("remove", item_name="Dagger", quantity=1, character_name="Vax")
    assert "Removed all Dagger" in res
