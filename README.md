# Agentic Dungeon Master 🎲 (Multi-Platform)


An AI-powered Dungeon Master that runs locally on your machine, connects to **Discord**, **Slack**, or **CLI**, and manages a D&D 5e campaign with persistent memory, anti-hallucination dice rolling, and secret DM logs.

## Features

### Core Engine
- **Fair Dice**: The bot cannot fake rolls. It commits to a DC/Consequence *before* asking you to roll.
- **Persistent Memory**: Uses local Markdown files to track the campaign.
- **Anti-Hallucination**: Checks a local rules file before creating rulings.
- **High-Fidelity Narration**: Captures and aggregates all DM dialogue across complex turns (e.g., between dice rolls).
- **Combat Stat Tracking**: Maintains persistent enemy HP, AC, and resource tracking in `secrets_log.md` to prevent mid-battle hallucinations.
- **Multi-Tenant (Multi-Campaign)**: Run a single DM instance that hosts multiple independent campaigns across different channels or platforms simultaneously.
- **Offline Capable**: Core tools run without any API keys.

### Discord Integration
- **Immersive Visuals**: Auto-generates images of scenes and monsters using Google Imagen.
- **Threaded Play**: Keeps campaign channels clean.
- **Roleplay Mode**: Users can register character names with `!iam`.

### Slack Integration
- **Multiplayer Interface**: Play D&D with friends in a Slack channel.
- **Access Control**: Limit usage to specific Users or Channels to protect your API quota.
- **Mention-Only**: In channels, the bot tracks chatter but only responds when tagged (`@DungeonMaster`).
- **Private Whispers**: The DM can send secret messages to specific players.

## Quick Start

### Path A: Local / MCP (Offline-Capable)
*Best for solo testing or using with a local AI client (Claude Desktop, Gemini, etc).*

0.  **Install Local Brain (Ollama)**:
    *(Skip if you already have it)*
    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &      # Start the server
    ollama pull llama3  # Download the brain (4GB)
    ```

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/yourusername/agentic-dm.git
    cd agentic-dm
    ./setup_slack.sh
    ```
2.  **Create a Campaign**:
    ```bash
    python3 src/wizard.py
    ```
    *Follow the prompts to generate your world.*
3.  **Run the Server**:
    ```bash
    python3 src/mcp_server.py
    ```
    *Or use the generated config to connect it to Claude Desktop.*

### Path B: Slackbot (Online)
*Best for playing with friends in a Slack channel.*

1.  **Install & Configure**:
    Follow steps in Path A, then copy the secrets template:
    ```bash
    cp .env.example .env
    ```
2.  **Add Tokens** (See [Setup Guide](slack_walkthrough.md)):
    *   `SLACK_APP_TOKEN` (Socket Mode)
    *   `SLACK_BOT_TOKEN`
    *   `GOOGLE_API_KEY` (Optional but Recommended)
3.  **Run the Bot**:
    ```bash
    ./play.sh -platform=slack
    ```

### Path C: Discord Bot (Online)
*Best for playing with friends in a Discord server.*

1.  **Install & Configure**:
    Follow steps in Path A, then copy the secrets template:
    ```bash
    cp .env.example .env
    ```
2.  **Add Tokens**:
    *   `DISCORD_BOT_TOKEN` (From Discord Developer Portal)
    *   `GOOGLE_API_KEY` (Optional but Recommended)
3.  **Run the Bot**:
    ```bash
    ./play.sh -platform=discord
    ```

### 🔑 API Key (Google AI Studio)
The bot uses the **Gemini 1.5 Pro** model. You need an API Key, but you **do not** need to pay.
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Create API Key** -> **Create API key in a new project**.
3. **Note on Billing**: You may see references to "Pay as you go" or Google Cloud projects.
    - The **Free Tier** (15 requests/min) is applied automatically to new keys.
    - You will **not** be charged unless you explicitly enable a paid billing account in the Google Cloud Console for that specific project.
4. Copy the key (starts with `AIza...`) and place it in your `.env` file:
   ```bash
   GOOGLE_API_KEY=AIzaSy...
   ```
   ```

### 🧠 Claude (Anthropic)
You can also use **Claude 3.5 Sonnet** as the brain.
1. Get an API Key from [Anthropic Console](https://console.anthropic.com/).
2. Add it to your `.env` file:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03...
   ```
3. **Priority System**: The bot checks keys in this order:
   - `GOOGLE_API_KEY` (Gemini) -> **Default if present.**
   - `ANTHROPIC_API_KEY` (Claude) -> Used if Google key is missing or commented out.
   - `FORCE_CLAUDE=1` -> Set this in `.env` to override the priority and force Claude.
   - No Keys -> Falls back to **Local (Ollama)**.

## Admin Commands
As the Admin, you can manage who joins the game dynamically:
- `!admin allow @user`: Adds a user to the allowed list.
- `!admin deny @user`: Bans a user.
- `!admin list`: Shows current allowed users.
- `!admin bind <campaign_name>`: 🎲 **Binds current channel to a specific campaign folder.**

## Documentation
- [Slack Setup Guide](slack_walkthrough.md): How to get the tokens.
- [Discord Setup Guide](discord_walkthrough.md): How to get the tokens.
- [Client Connection Guide](CLIENTS.md): Using Claude Desktop & Native CLI.
- [Player Guide](walkthrough.md): How to use the bot commands.
- **[New Feature Details](file:///home/verran/dev/gemini_dm/FEATURES.md)**: Deep dive into Combat Tracking and Narration logic.

## Feature Capabilities
The bot is designed to be **Offline First**, with optional Cloud enhancements.

| Status | Meaning |
| :---: | :--- |
| 🟢 | **Native**: Works 100% locally out of the box. |
| 🟡 | **Adaptive**: Works locally, but delegates complex tasks to the Human/Local AI if the Cloud Key is missing. |
| 🔴 | **Cloud Only**: Requires `GOOGLE_API_KEY` for the specific feature. |

| Feature | Status | Behavior without API Key |
| :--- | :---: | :--- |
| **Dice Rolling** | 🟢 | Full functionality (Local Math). |
| **Campaign Wizard** | 🟢 | Full functionality (Local Files). |
| **Rules Lookup** | 🟢 | Full functionality (Regex Search). |
| **Basic Name Gen** | 🟢 | Full functionality (Elf, Dwarf, Human, Town). |
| **Rule Validation** | 🟡 | **Delegates**: Returns raw stats to you/Local AI to make the ruling. |
| **Exotic Name Gen** | 🟡 | **Delegates**: Returns "Custom names require key" -> Bot invents one itself. |
| **Combat Tracking** | 🟢 | Full functionality (Persistent Markdown state). |
| **Session Summary** | 🟡 | **Manual**: Accepts `manual_summary` from Client instead of auto-generating. |
| **Image Generation** | 🔴 | **Disabled**: Falls back to vivid text descriptions. |

## Legal
This project is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

## License
MIT
