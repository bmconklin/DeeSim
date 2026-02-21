import os
import json
from contextvars import ContextVar

# --- Context & Registry Management ---
active_campaign_ctx: ContextVar[str | None] = ContextVar("active_campaign", default=None)
REGISTRY_PATH = os.path.join(os.getcwd(), "campaign_registry.json")

def get_campaign_for_channel(platform_id: str, channel_id: str) -> str | None:
    """Returns the campaign name bound to a specific channel."""
    if not os.path.exists(REGISTRY_PATH):
        return None
    try:
        with open(REGISTRY_PATH, "r") as f:
            registry = json.load(f)
        return registry.get(f"{platform_id}:{channel_id}")
    except:
        return None

def bind_channel_to_campaign(platform_id: str, channel_id: str, campaign_name: str):
    """Binds a platform/channel to a campaign folder."""
    registry: dict[str, str] = {}
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r") as f:
                registry = json.load(f)
        except: pass
    registry[f"{platform_id}:{channel_id}"] = campaign_name
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

def set_active_campaign(campaign_name: str):
    """Sets the campaign context for the current thread/task."""
    return active_campaign_ctx.set(campaign_name)

# --- Campaign Path Resolution ---
CAMPAIGNS_DIR = os.environ.get("DM_CAMPAIGNS_DIR", os.path.join(os.getcwd(), "campaigns"))
ACTIVE_CAMPAIGN = os.environ.get("DM_ACTIVE_CAMPAIGN", "default")

def get_campaign_root():
    """Dynamically resolves the root directory for the active campaign."""
    # Priority 1: Managed Context (Thread/Task Local)
    ctx_name = active_campaign_ctx.get()
    if ctx_name:
        root = os.path.join(CAMPAIGNS_DIR, ctx_name)
        if not os.path.exists(root):
             os.makedirs(root, exist_ok=True)
        return root
        
    # Priority 2: System-level Override (DM_CAMPAIGN_ROOT)
    env_root = os.environ.get("DM_CAMPAIGN_ROOT")
    if env_root:
        return env_root
        
    root = os.path.join(CAMPAIGNS_DIR, ACTIVE_CAMPAIGN)
    if not os.path.exists(root):
         os.makedirs(root, exist_ok=True)
    return root

def get_campaign_config(campaign_name: str | None = None) -> dict:
    """Loads the campaign-specific config.json."""
    if not campaign_name:
        root = get_campaign_root()
    else:
        root = os.path.join(CAMPAIGNS_DIR, campaign_name)
        
    config_path = os.path.join(root, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_current_session_dir():
    """Returns the directory of the current open session."""
    root = get_campaign_root()
    current_session_file = os.path.join(root, "current_session.txt")
    if os.path.exists(current_session_file):
        with open(current_session_file, "r") as f:
            session_name = f.read().strip()
        return os.path.join(root, session_name)
    else:
        return root
