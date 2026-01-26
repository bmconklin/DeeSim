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
        if user_id and str(user_id) in [u.strip() for u in env_allowed_users.split(",")]:
            allowed = True
    
    if user_id and str(user_id) in json_users:
        allowed = True
        
    # If we have user restrictions and the user wasn't found -> Block
    if (env_allowed_users or json_users) and not allowed:
        return False

    # Channels
    if env_allowed_channels:
        channels_list = [c.strip() for c in env_allowed_channels.split(",")]
        if channel_id and str(channel_id) not in channels_list:
            return False
            
    return True
