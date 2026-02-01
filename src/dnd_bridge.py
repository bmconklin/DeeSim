import os
import sys

# Resolve project root from this file's location (works regardless of cwd)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_PROJECT_ROOT)

from src.dnd.core.cache import APICache
from src.dnd.core import tools as dnd_tools

# Mock FastMCP App to capture the tools
class MockApp:
    def __init__(self):
        self.registered_tools = {}

    def tool(self, name=None):
        def decorator(f):
            tool_name = name or f.__name__
            self.registered_tools[tool_name] = f
            return f
        return decorator

# Initialize Cache
# Store cache in .dnd_cache to keep it clean
CACHE_DIR = os.path.join(_PROJECT_ROOT, ".dnd_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize components
_app = MockApp()
_cache = APICache(ttl_hours=24, persistent=True, cache_dir=CACHE_DIR)

# Register tools into our mock app
print("Initializing D&D Tools Bridge...")
dnd_tools.register_tools(_app, _cache)
print("D&D Tools Bridge Initialized.")

# --- Public API for Bot ---

def search_dnd_rules(query: str) -> dict:
    """
    Search the official D&D 5e API for rules, spells, monsters, and more.
    Use this to look up specific mechanics or stats.
    """
    func = _app.registered_tools.get("search_all_categories")
    if func:
        return func(query)
    return {"error": "Tool not found"}

def verify_dnd_statement(statement: str) -> dict:
    """
    Verify a statement about D&D rules (e.g. 'Can wizards wear armor?').
    """
    func = _app.registered_tools.get("verify_with_api")
    if func:
        return func(statement)
    return {"error": "Tool not found"}

def get_spell_info(min_level: int = 0, max_level: int = 9, school: str = None) -> dict:
    """
    Find spells by level range and optional school.
    """
    func = _app.registered_tools.get("filter_spells_by_level")
    if func:
        return func(min_level, max_level, school)
    return {"error": "Tool not found"}

def find_monster(min_cr: float = 0, max_cr: float = 30) -> dict:
    """
    Find monsters by Challenge Rating (CR).
    """
    func = _app.registered_tools.get("find_monsters_by_challenge_rating")
    if func:
        return func(min_cr, max_cr)
    return {"error": "Tool not found"}
