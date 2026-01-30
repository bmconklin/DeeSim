import os
import json

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
        # Store as string to handle Slack (U123) and Discord (123456789)
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"].append(user_id)
            self.save()
            return True
        return False
        
    def remove_user(self, user_id):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            self.data["users"].remove(user_id)
            self.save()
            return True
        return False

    def get_allowed_users(self):
        return self.data["users"]

# Singleton instance
permissions = PermissionsManager()

def is_allowed(user_id=None, channel_id=None, server_id=None, platform_id=None):
    # 1. Check Env Vars (Static)
    env_allowed_users = os.environ.get("ALLOWED_USER_IDS", "")
    env_allowed_channels = os.environ.get("ALLOWED_CHANNEL_IDS", "")
    
    # Platform-specific Server/Workspace overrides
    env_global = os.environ.get("ALLOWED_SERVER_IDS", "")
    if platform_id == "discord":
        val = os.environ.get("DISCORD_ALLOWED_SERVER_IDS")
        env_allowed_servers = val if val is not None else env_global
    elif platform_id == "slack":
        val = os.environ.get("SLACK_ALLOWED_WORKSPACE_IDS")
        env_allowed_servers = val if val is not None else env_global
    else:
        env_allowed_servers = env_global
    
    # If NO access control is set at all (Env or JSON), allow all
    json_users = permissions.get_allowed_users()
    
    if not env_allowed_users and not env_allowed_channels and not env_allowed_servers and not json_users:
        return True

    # 2. Check Allow Lists
    # Users
    user_match = True
    if env_allowed_users or json_users:
        user_match = False # Default to false if restricted
        if user_id:
             if env_allowed_users and str(user_id) in [u.strip() for u in env_allowed_users.split(",")]:
                 user_match = True
             if str(user_id) in json_users:
                 user_match = True

    # Channels
    channel_match = True
    if env_allowed_channels:
        channel_match = False
        if channel_id and str(channel_id) in [c.strip() for c in env_allowed_channels.split(",")]:
            channel_match = True

    # Servers (Platform Aware)
    server_match = True
    if env_allowed_servers:
        server_match = False
        if server_id and str(server_id) in [s.strip() for s in env_allowed_servers.split(",")]:
            server_match = True
            
    # Logic: ALL active restrictions must be met. 
    return user_match and channel_match and server_match
