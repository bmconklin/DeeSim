
import os
import sys
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
    system_instruction=get_system_instruction(),
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
    print(f"Campaign Root: {dm_utils.CAMPAIGN_ROOT}")

@client.event
async def on_message(message):
    # Ignore own messages
    if message.author == client.user:
        return

    user_id = str(message.author.id)
    user_name = message.author.name
    channel_id = str(message.channel.id)
    text = message.content
    
    # 1. Check for Admin Commands
    if text.startswith("!admin"):
        # Simple admin check - could be improved
        admin_id = os.environ.get("ADMIN_DISCORD_ID")
        if not admin_id or user_id != admin_id:
            await message.channel.send("⛔ You are not the Dungeon Master.")
            return
            
        # ... Admin logic similar to Slack, but using discord API ...
        # For now, let's keep it simple or implement later.
        await message.channel.send("Mending Admin commands not fully ported to Discord yet.")
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
        # Warning: Engine is synchronous, Discord is async. 
        # For a hackathon/MVP, blocking here is 'okay' but ideally runs in executor.
        
        response_text = engine.process_message(
            user_id=user_id,
            user_name=user_name,
            message_text=text,
            platform_id="discord",
            attachments=image_parts,
            channel_id=channel_id
        )
        
        # Split response if > 2000 chars (Discord limit)
        if len(response_text) > 2000:
            # Naive split
            chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(response_text)
            
    else:
        # Passive Buffer
        engine.buffer_message(
            user_id=user_id,
            user_name=user_name,
            message_text=text,
            channel_id=channel_id
        )

if __name__ == "__main__":
    client.run(os.environ["DISCORD_BOT_TOKEN"])
