
import os
import datetime
from google.genai import types
import dm_utils
import llm_bridge
from .permissions import is_allowed

class GameEngine:
    def __init__(self, system_instruction: str, tools_list: list):
        self.system_instruction = system_instruction
        self.tools_list = tools_list
        self.model_name = os.environ.get("MODEL_NAME", "gemini-2.5-flash")
        
        # Initialize Context
        self.history = dm_utils.load_chat_snapshot()
        print(f"✨ [Engine] Loaded {len(self.history)} messages from history.")
        
        self.chat = llm_bridge.get_chat_session(
            model_name=self.model_name,
            history=self.history,
            tools=self.tools_list,
            system_instruction=self.system_instruction
        )

    def process_message(self, user_id: str, user_name: str, message_text: str, platform_id: str, attachments: list = None, channel_id: str = None) -> str:
        """
        Main Game Loop:
        1. Check Permissions
        2. Inject Context (Name, Time, Buffer, Wizard)
        3. Call LLM
        4. Save History
        5. Return Response Text
        """
        # 1. Permission Check
        if not is_allowed(user_id=user_id, channel_id=channel_id):
            return f"🔒 You are not in the Book of Allowed Heroes. Ask the DM (`!admin allow {user_id}`)."

        # 2. Context Injection
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

        # 3. Call LLM
        try:
            content = [final_text]
            if attachments:
                # Expect attachments to be formatted as Types.Part or similar
                content.extend(attachments)
                
            response = self.chat.send_message(content)
            
            # 4. Save History
            try:
                dm_utils.save_chat_snapshot(self.chat.get_history())
            except Exception as h_err:
                print(f"[Engine] Failed to save history: {h_err}")
                
            return response.text
            
        except Exception as e:
            error_str = str(e)
            print(f"[Engine] LLM Error: {error_str}")
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                return "⏳ The magical winds are calm (Rate Limit Exceeded). Please wait a moment and try again."
            else:
                return f"I encountered a magical disturbance (Error: {error_str})"

    def buffer_message(self, user_id: str, user_name: str, message_text: str, channel_id: str = None):
        """Passively buffer messages."""
        if is_allowed(user_id, channel_id):
            char_name = dm_utils.get_character_name(user_id)
            author_name = char_name if char_name != "Unknown Hero" else user_name
            dm_utils.append_to_context_buffer(author_name, message_text)
