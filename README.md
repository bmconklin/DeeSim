# Agentic Dungeon Master 🎲 (Slackbot Edition)

An AI-powered Dungeon Master that runs locally on your machine, connects to Slack, and manages a D&D 5e campaign with persistent memory, anti-hallucination dice rolling, and secret DM logs.

## Features

### Core Engine (Local & Slack)
- **Fair Dice**: The bot cannot fake rolls. It commits to a DC/Consequence *before* asking you to roll.
- **Persistent Memory**: Uses local Markdown files to track the campaign.
- **Anti-Hallucination**: Checks a local rules file before creating rulings.
- **Offline Capable**: Core tools run without any API keys.

### Slack Integration
- **Multiplayer Interface**: Play D&D with friends in a Slack channel.
- **Access Control**: Limit usage to specific Users or Channels to protect your API quota.
- **Mention-Only**: In channels, the bot tracks chatter but only responds when tagged (`@DungeonMaster`).
- **Private Whispers**: The DM can send secret messages to specific players.

## Quick Start

### Path A: Local / MCP (Offline-Capable)
*Best for solo testing or using with a local AI client (Claude Desktop, Gemini, etc).*

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
    python3 src/bot.py
    ```

## Admin Commands
As the Admin, you can manage who joins the game dynamically:
- `!admin allow @user`: Adds a user to the allowed list.
- `!admin deny @user`: Bans a user.
- `!admin list`: Shows current allowed users.

## Documentation
- [Slack Setup Guide](slack_walkthrough.md): How to get the tokens.
- [Player Guide](walkthrough.md): How to use the bot commands.

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
| **Session Summary** | 🟡 | **Manual**: Accepts `manual_summary` from Client instead of auto-generating. |
| **Image Generation** | 🔴 | **Disabled**: Falls back to vivid text descriptions. |

## License
MIT
