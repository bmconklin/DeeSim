
import os
import sys
import asyncio
import discord
import requests
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Check for Discord Token
if not os.environ.get("DISCORD_BOT_TOKEN"):
    print("Error: DISCORD_BOT_TOKEN not found in .env.")
    print("Please add it to run the Discord bot.")
    sys.exit(1)

import dm_utils
from google.genai import types

# --- Setup Game Engine ---
from core.engine import GameEngine
from bot import tools_list, get_system_instruction # Reuse tools from bot.py or move tools to core

# Initialize Engine
engine = GameEngine(
    tools_list=tools_list
)

# --- Discord Client ---
intents = discord.Intents.default()
intents.message_content = True # Required to read messages

client = discord.Client(intents=intents)

def process_attachments(message):
    """
    Downloads images from Discord message attachments.
    """
    if not message.attachments:
        return []
        
    parts = []
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            print(f"📸 Found image: {attachment.filename}")
            try:
                # Discord URLs are public (with signature), so requests.get works
                response = requests.get(attachment.url)
                if response.status_code == 200:
                    image_data = response.content
                     # Create Part object
                    parts.append(types.Part.from_bytes(data=image_data, mime_type=attachment.content_type))
                else:
                    print(f"Failed to download image: {response.status_code}")
            except Exception as e:
                print(f"Error processing image: {e}")
                
    return parts

@client.event
async def on_ready():
    print(f'🤖 Agentic DM (Discord) logged in as {client.user}')

@client.event
async def on_message(message):
    # Ignore own messages
    if message.author == client.user:
        return

    user_id = str(message.author.id)
    user_name = message.author.name
    channel_id = str(message.channel.id)
    server_id = str(message.guild.id) if message.guild else None
    text = message.content
    
    # Check Allowed Channel (if configured)
    allowed_channel = os.environ.get("DISCORD_ALLOWED_CHANNEL_ID")
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    if allowed_channel and not is_dm and channel_id != allowed_channel:
        # Ignore messages in other channels
        return

    # Set Campaign Context 
    campaign_name = dm_utils.get_campaign_for_channel("discord", channel_id)
    token = None
    if campaign_name:
        token = dm_utils.set_active_campaign(campaign_name)
    
    try:

        # 1. Check for Admin Commands
        if text.startswith("!admin"):
            admin_id = os.environ.get("ADMIN_DISCORD_ID")
            if not admin_id or user_id != admin_id:
                await message.channel.send("⛔ You are not the Dungeon Master.")
                return

            parts = text.split()
            if len(parts) < 2:
                await message.channel.send("Usage: `!admin allow <ID>`, `!admin bind <campaign>`")
                return

            command = parts[1]
            if command == "bind":
                if len(parts) < 3:
                    await message.channel.send("Usage: `!admin bind <campaign_name>`")
                    return
                campaign_name = parts[2]
                dm_utils.bind_channel_to_campaign("discord", channel_id, campaign_name)
                await message.channel.send(f"✅ Success! Channel is now bound to campaign `{campaign_name}`.")
                return

            # Fallback for other admin commands
            await message.channel.send(f"Admin command '{command}' received (not fully implemented in Discord).")
            return

        # 1.5 Special Commands (Global)
        if text.startswith("!help"):
            help_text = """**📜 Agentic DM Commands**

    **🎨 Visualization**
    `!visualize` - Auto-detect and paint the current scene.
    `!visualize <topic>` - Describe and paint a specific topic.
    `!visualize session` - Paint the most epic moment of the session.
    `!generate <prompt>` - Manually force an image generation (skip description).
    `!hide` - Clear stuck image prompts.

    **👤 Player**
    `!iam <Name>` - Register your character name.

    **🛠️ Tools**
    `!forget` - Undo the last interaction (fixes "refusal" loops).
    `!wrapup` - Summarize and archive current session.
    `!startsession` - Create folder for next session."""
            await message.channel.send(help_text)
            return

        if text.startswith("!visualize"):
            # Creative Generation: !visualize [optional topic]
            topic = text.replace("!visualize", "").strip()

            if not topic:
                # Context-based generation
                await message.channel.send(f"🎨 Asking DM to visualize the current scene...")
                prompt_injection = f"(System Command): The user wants a visualization of the CURRENT SCENE based on recent gameplay. 1. Describe the current moment vividly. 2. Call `generate_scene_image` (or write '**Image Prompt:**') to generate it."
            elif topic.lower() in ["session", "highlight", "recap", "epic"]:
                # Session-wide recap generation
                await message.channel.send(f"🎨 Asking DM to find and paint the session's most epic moment...")
                prompt_injection = f"(System Command): The user wants a visualization of the MOST EPIC MOMENT from this entire session. 1. Review the chat history. 2. Choose the most dramatic, visually striking scene that occurred. 3. Describe it vividly. 4. Call `generate_scene_image` (or write '**Image Prompt:**') to generate it."
            else:
                # Specific topic generation
                await message.channel.send(f"🎨 Asking DM to visualize: *{topic}*...")
                prompt_injection = f"(System Command): The user wants a visualization of '{topic}'. 1. Describe this scene vividly. 2. Call `generate_scene_image` (or write '**Image Prompt:**') to generate it."

            # We process this as a normal message but with the injection

            # We process this as a normal message but with the injection
            # The response will trigger the auto-generation logic below.
            response_text = await asyncio.to_thread(
                engine.process_message,
                user_id=user_id,
                user_name=user_name,
                message_text=prompt_injection,
                platform_id="discord",
                attachments=[],
                channel_id=channel_id,
                server_id=server_id
            )

            await message.channel.send(response_text)

            # The bottom of this function will handle the auto-generation check!
            # logic continues to auto-gen block...
            # We need to ensure we don't return early here, so we jump to the shared block.
            # Refactoring slightly to allow fall-through or duplicate the check.

            # Let's just duplicate the check for now to be safe and simple.
            if os.path.exists(dm_utils.get_pending_image_path()) or dm_utils.extract_and_save_prompt_from_text(response_text):
                 await message.channel.send("🎨 Auto-generating scene visualization...")
                 image_bytes, result = await asyncio.to_thread(dm_utils.generate_image_from_pending)
                 if image_bytes:
                    try:
                        import io
                        file = discord.File(fp=io.BytesIO(image_bytes), filename="scene_visual.png")
                        await message.channel.send(content=f"Visual for: *{result}*", file=file)
                    except Exception as e:
                        await message.channel.send(f"❌ Upload Failed: {e}")
                 else:
                    await message.channel.send(f"❌ Generation Failed: {result}")
            return

        if text.startswith("!generate"):
            # Manual Override: !generate <prompt>
            prompt = text.replace("!generate", "").strip()
            if not prompt:
                await message.channel.send("Usage: `!generate <description>`")
                return

            await message.channel.send(f"🎨 Manually generating: *{prompt}*...")
            # Save prompt manually
            dm_utils.propose_image(prompt)
            # Trigger generation immediately
            image_bytes, result = await asyncio.to_thread(dm_utils.generate_image_from_pending)

            if image_bytes:
                try:
                    import io
                    file = discord.File(fp=io.BytesIO(image_bytes), filename="scene_visual.png")
                    await message.channel.send(content=f"Visual for: *{result}*", file=file)
                except Exception as e:
                    await message.channel.send(f"❌ Upload Failed: {e}")
            else:
                 await message.channel.send(f"❌ Generation Failed: {result}")
            return

        if text.startswith("!forget"):
            # Helper to clear recent memory if bot gets stuck/refuses
            try:
                removed = dm_utils.undo_last_message()
                await message.channel.send(f"🧠 *Poof!* I have forgotten the last interaction ({removed}). Try again.")
            except Exception as e:
                await message.channel.send(f"❌ Failed to forget: {e}")
            return

        if text.startswith("!wrapup"):
            await message.channel.send("📜 Compacting session log and generating summary...")
            try:
                # Summarize current session
                summary_result = await asyncio.to_thread(dm_utils.summarize_and_compact_session_logic)
                await message.channel.send(summary_result)
                await message.channel.send("✅ Session wrapped! Type `!startsession` to begin the next chapter.")
            except Exception as e:
                await message.channel.send(f"❌ Wrap-up failed: {e}")
            return

        if text.startswith("!startsession"):
            await message.channel.send("🌅 Initializing new session...")
            try:
                # We need the summary from the previous session to seed the next one.
                # dm_utils.start_new_session_logic takes 'summary_of_previous'.
                # We'll try to read it from the log we just compacted.

                # 1. Read the summary from current session log
                log_path, _ = dm_utils.get_log_paths()
                with open(log_path, "r") as f:
                    content = f.read()

                # Extract summary section (simple heuristic)
                if "## Summary" in content:
                    summary = content.split("## Summary")[1].split("##")[0].strip()
                else:
                    summary = "Session ended without automated summary."

                # 2. Start new session
                result = dm_utils.start_new_session_logic(summary)
                await message.channel.send(f"🎉 {result}")

            except Exception as e:
                 await message.channel.send(f"❌ Failed to start new session: {e}")
            return

        if text.startswith("!iam"):
            # Format: !iam <Character Name>
            import re
            match = re.search(r"!iam\s+(.+)", text, re.IGNORECASE)
            if not match:
                await message.channel.send("Usage: `!iam <Character Name>` (e.g. `!iam Grognak`)")
            else:
                char_name = match.group(1).strip()
                # Register using Discord ID
                result = dm_utils.register_player(user_id, char_name)
                await message.channel.send(result)
            return

        if text.startswith("!show"):
             await message.channel.send("Use `!generate` or wait for auto-generation. `!show` is deprecated.")
             return

        if text.startswith("!hide"):
            result = dm_utils.clear_pending_image()
            await message.channel.send(f"🗑️ {result}")
            return

        # 2. Check for DM (Direct Message) or Mention
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = client.user in message.mentions

        if is_dm or is_mention:
            # Active Response
            print(f"Received message from {user_name} ({user_id})")

            # Clean mention from text
            if is_mention:
                 text = text.replace(f"<@{client.user.id}>", "").strip()

            image_parts = process_attachments(message)

            # Delegate to Engine
            # Run in a separate thread to avoid blocking Discord heartbeat
            response_text = await asyncio.to_thread(
                engine.process_message,
                user_id=user_id,
                user_name=user_name,
                message_text=text,
                platform_id="discord",
                attachments=image_parts,
                channel_id=channel_id,
                server_id=server_id
            )

            if not response_text:
                response_text = "..."

            # Split response if > 2000 chars (Discord limit)
            if len(response_text) > 2000:
                # Naive split
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response_text)



            # 3. Check for Pending Image (Auto-Generate)
            # Check explicit tool call OR fallback scrape
            has_pending = os.path.exists(dm_utils.get_pending_image_path())

            if not has_pending:
                # Try to partial-match from text (Fallback)
                if dm_utils.extract_and_save_prompt_from_text(response_text):
                    has_pending = True

            if has_pending:
                await message.channel.send("🎨 Auto-generating scene visualization...")
                image_bytes, result = await asyncio.to_thread(dm_utils.generate_image_from_pending)

                if image_bytes:
                    try:
                        import io
                        file = discord.File(fp=io.BytesIO(image_bytes), filename="scene_visual.png")
                        await message.channel.send(content=f"Visual for: *{result}*", file=file)
                    except Exception as e:
                        await message.channel.send(f"❌ Upload Failed: {e}")
                else:
                     await message.channel.send(f"❌ Generation Failed: {result}")

        else:
            # Passive Buffer
            engine.buffer_message(
                user_id=user_id,
                user_name=user_name,
                message_text=text,
                platform_id="discord",
                channel_id=channel_id,
                server_id=server_id
            )
    finally:
        if token:
            dm_utils.active_campaign_ctx.reset(token)

if __name__ == "__main__":
    client.run(os.environ["DISCORD_BOT_TOKEN"])
