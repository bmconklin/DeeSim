# Agentic Dungeon Master - Walkthrough

## Prerequisites
- **Python 3**: Must be installed.
- **AI Agent Client**: Claude Desktop, Claude CLI, or similar MCP-compatible client.
- **API Key**: You need an active API key for your chosen LLM (e.g. Anthropic API key).

## Setup Guide

### 1. Run the Installer
Open your terminal in this directory and run:

```bash
./start.sh
```

This will:
1. Create a Python virtual environment (`venv`).
2. Install the `mcp` library.
3. Launch the **Setup Wizard**.

### 2. Follow the Wizard
- **Campaign Name**: Enter a name for your campaign (e.g., "Mines of Phandelver").
- **Client Selection**: Choose which AI client you use (e.g., "Claude Desktop").

The wizard will generate:
- A `campaigns/<your_campaign_name>` folder with `session_log.md` and `secrets_log.md`.
- A `system_prompt.txt` file.
- A Client Configuration file (e.g., `claude_desktop_config.json`).

### 3. Connect to your Client
The wizard prints a command to copy the config file.
**Example for Claude Desktop (Mac):**
```bash
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```
*(Note: If you already have a config file there, manually merge the "mcpServers" section instead of overwriting.)*

### 4. Provide the System Prompt
1. Open `campaigns/<your_campaign_name>/system_prompt.txt`.
2. Copy the contents.
3. Paste it into your Agent's "System Prompt" or "Custom Instructions" field.

## Verification
To verify the Agent is being "honest":
1. Ask the Agent to "Roll for initiative for a goblin".
2. **Check the logs**:
   Open `campaigns/<your_campaign>/session_log.md`.
   You should see a new entry with the exact roll result and timestamp.

## Customization
- **Rules**: Edit `src/initial_rules.txt` to add specific rules text.
- **World Info**: Edit `campaigns/<your_campaign>/world_info.md` to establish true facts (NPC names, locations) that the Agent should respect.

## Roll Workflow (Commitment)
When playing with "Manual Player Rolls":
1.  The Agent will decide on a DC and a Consequence for failure.
2.  It will run `request_player_roll` to lock these values into the **Secrets Log**.
3.  *Then* it will ask you to roll.
4.  This ensures the DM can't change the outcome based on your roll result.

## Session Management
- **Automatic Folders**: Your campaign starts in `session_1`.
- **End of Session**: Ask the Agent to "End this session". It will use the `start_new_session` tool to:
    1. Archive the current session log.
    2. Create a `session_2` folder.
    3. Seed the new session with a summary.

## Session Compactor
At the end of a game night, the Agent can tidy up the logs.
- **Tool**: `end_session_and_compact()`
- **What it does**:
    1. Reads the full session log.
    2. Uses AI to summarize narrative events (removing dice/chatter).
    3. **Creates a Highlight Reel** (Nat 20s, epic moments).
    4. Archives the full log to `session_N_full_archive.md`.
    5. Overwrites `session_log.md` with the clean summary.
- **Usage**: Just tell the bot "That's a wrap for tonight, please summarize and close the session."

## Introduction
This bot is an "Agentic Tool" for Gemini or Claude. YOU communicate with the logic/tools, and IT handles the game state.

**Key Features:**
- **Offline First**: Core tools (Dice, Rules, Logging) work without any API keys.
- **Local Brain**: Can connect to a Local LLM (Ollama) if no Google Key is present.
- **AI Enhanced**: Add a Google API Key to enable Image Gen, Validation, and Summaries.
- **Fair Play**: Dice rolls and rule checks are logged to a verifiable file first.

## Private Whispers
The Agent can now send private messages (DMs) to specific players.
- **Example**: "You notice the rogue pickpocketing the merchant, but no one else sees it."
- **Tool**: `send_dm(character_name, message)`
- **Requirement**: Players must register with `!iam CharacterName` first.

## Random Name Generator
To avoid "Bob the Goblin" syndrome, the bot uses a dedicated algorithm.
- **Tool**: `generate_name(race)`
- **Command**: `!name <race>` (e.g., `!name goblin`, `!name alien`, `!name town`).
- **Feature**: Uses `fantasynames` for basics (Elf/Dwarf/Human/Place). For anything else (Orcs, Gnomes, Custom), it **uses the AI** to invent a creative name instantly.

## Interactive Image Generation
The DM can visualize the scene for you, but only if you want it to.
- **Workflow**:
    1. Bot says: "I have a visual for this... Type `!show` to see it."
    2. Player types: `!show` (or `!hide` to dismiss).
    - If you insist or explain ("I have a Ring of Wishes"), it will **allow** it. It is not the "Fun Police".
    - **Offline Mode**: If no API Key is present, it delegates the judgment to the Local AI (you) by providing the raw Party Status data.
- **Why**: Keeps the channel clean and saves API usage for when it matters.

## Multimodal Support (Images)
You can directly upload images (maps, character sheets, monster art) to the Slack channel.
1. Drag and drop a file into the channel.
2. In the message box (optional), tag the bot: `Here is the map of the dungeon @DeeSim`.
3. The Agent will "see" the image and can use it for context (e.g. "I move to room 4 on the map").
