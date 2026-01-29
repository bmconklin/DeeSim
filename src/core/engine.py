
import os
import time
import datetime
from google.genai import types
import dm_utils
import llm_bridge
from .permissions import is_allowed

class GameEngine:
    def __init__(self, tools_list: list):
        self.tools_list = tools_list
        self.sessions = {} # campaign_name -> ChatSession
        provider, resolved_name = llm_bridge.resolve_model_config()
        self.model_name = resolved_name
        print(f"✨ [Engine] Multitenant Initialized with {provider} model: {self.model_name}")

    def get_campaign_session(self, campaign_name: str):
        """Retrieves or initializes a chat session for a specific campaign."""
        if campaign_name in self.sessions:
            return self.sessions[campaign_name]
        
        # We assume the context is already set by the caller (process_message)
        history = dm_utils.load_chat_snapshot()
        system_instruction = dm_utils.get_system_instruction()
        
        print(f"✨ [Engine] Loading session for campaign: {campaign_name} ({len(history)} messages)")
        
        session = llm_bridge.get_chat_session(
            model_name=self.model_name,
            history=history,
            tools=self.tools_list,
            system_instruction=system_instruction
        )
        self.sessions[campaign_name] = session
        return session

    def handle_admin_bind(self, platform_id, channel_id, user_id, message_text):
        """Handles the !admin bind <campaign> command."""
        # Simple permission check (we can refine this)
        # For now, let's assume anyone who knows the command can use it, or check ADMIN_USER_ID
        parts = message_text.split()
        if len(parts) < 3:
            return "Usage: `!admin bind <campaign_name>`"
        
        campaign_name = parts[2]
        dm_utils.bind_channel_to_campaign(platform_id, channel_id, campaign_name)
        return f"✅ Success! Channel `{channel_id}` is now bound to campaign `{campaign_name}`. Good luck, adventurers!"

    def process_message(self, user_id: str, user_name: str, message_text: str, platform_id: str, attachments: list = None, channel_id: str = None, server_id: str = None) -> str:
        """
        Main Game Loop (Multitenant):
        1. Determine Campaign
        2. Set Context
        3. Run turn
        """
        # 1. Determine Campaign
        campaign_name = dm_utils.get_campaign_for_channel(platform_id, channel_id)
        print(f"🎬 [Engine] Routing {platform_id} message (Channel: {channel_id}) to Campaign: {campaign_name or 'PENDING_BIND'}")
        
        if not campaign_name:
            # Special logic for CLI or first-time setup
            if platform_id == "local":
                 campaign_name = dm_utils.ACTIVE_CAMPAIGN
            elif message_text.startswith("!admin bind"):
                 return self.handle_admin_bind(platform_id, channel_id, user_id, message_text)
            else:
                 return f"❌ This channel is not yet registered to a campaign. An admin must run `!admin bind <name>` (e.g., `!admin bind oneshot`).\n\n(Channel ID: `{channel_id}`)"

        # 2. Set Context for all nested util calls in this thread
        token = dm_utils.set_active_campaign(campaign_name)
        try:
        
            # Permission Check
            if not is_allowed(user_id=user_id, channel_id=channel_id, server_id=server_id, platform_id=platform_id):
                platform_label = "Slack Workspace" if platform_id == "slack" else "Discord Server"
                return f"🔒 [Access Denied] You are not in the Book of Allowed Heroes for this {platform_label}.\nAsk the DM to run `!admin allow <@{user_id}>`."

            session = self.get_campaign_session(campaign_name)

            # Context Injection
            final_text = message_text
            
            # Player Name
            char_name = dm_utils.get_character_name(user_id)
            if char_name != "Unknown Hero":
                 final_text = f"(Character: {char_name}) {final_text}"
            elif user_name:
                 final_text = f"(User: {user_name}) {final_text}"

            # Passive Buffer
            buffered_context = dm_utils.get_and_clear_context_buffer()
            if buffered_context:
                final_text = f"[Background Context - Untagged Conversation]:\n{buffered_context}\n\n[Direct Interaction]:\n{final_text}"

            # Time Gap / New Session
            hours_since = dm_utils.get_hours_since_last_message()
            if hours_since > 4.0:
                system_note = f"[System Note: It has been {hours_since:.1f} hours since the last game interaction. This is likely a new session. Please welcome the players back, mention the break, and ask for a roll call to see who is present before continuing.]"
                final_text = f"{system_note}\n\n{final_text}"

            # Setup Wizard
            setup_step = dm_utils.get_setup_step()
            if setup_step < 4:
                setup_instructions = dm_utils.get_setup_instructions(setup_step)
                final_text = f"{setup_instructions}\n\n{final_text}"

            # 3. Call LLM with Retry Logic
            max_retries = 3
            base_delay = 2
            
            for attempt in range(max_retries + 1):
                try:
                    content = [final_text]
                    if attachments:
                        content.extend(attachments)
                    
                    # session (ChatSession) holds history and tools
                    response = session.send_message(content, timeout=90)
                    
                    # 4. Save History (Context is set, so snapshots save to correct folder)
                    try:
                        dm_utils.save_chat_snapshot(session.get_history())
                    except Exception as h_err:
                        print(f"[Engine] Failed to save history: {h_err}")
                        
                    text_out = response.text
                    if not text_out:
                        text_out = "..."
                        
                    return text_out

                except Exception as e:
                    error_str = str(e)
                    print(f"[Engine] LLM Error (Attempt {attempt+1}/{max_retries+1}): {error_str}")
                    
                    # Check for 503, Overloaded, or Network/SSL Timeouts
                    error_lower = error_str.lower()
                    is_transient = (
                        "503" in error_str or 
                        "overloaded" in error_lower or
                        "timed out" in error_lower or
                        "ssl" in error_lower or
                        "connection" in error_lower
                    )
                    
                    if is_transient and attempt < max_retries:
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                    
                    # Final Error Handling
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        return "⏳ The magical winds are calm (Rate Limit Exceeded). Please wait a moment."
                    elif is_transient:
                        return "😵 The spirits are overwhelmed (Model Overloaded). Please try again in a moment."
                    else:
                        return f"I encountered a magical disturbance (Error: {error_str})"
        finally:
            # Clear context
            dm_utils.active_campaign_ctx.reset(token)

    def buffer_message(self, user_id: str, user_name: str, message_text: str, platform_id: str, channel_id: str = None, server_id: str = None):
        """Passively buffer messages."""
        if is_allowed(user_id, channel_id, server_id, platform_id):
            char_name = dm_utils.get_character_name(user_id)
            author_name = char_name if char_name != "Unknown Hero" else user_name
            dm_utils.append_to_context_buffer(author_name, message_text)
