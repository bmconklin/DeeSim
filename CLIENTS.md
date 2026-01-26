# Client Guide: How to Connect 🔌

To play D&D with this bot, you need a "Client" that can talk to our tools (Dice, Logs, Rules).
You cannot just paste the prompt into a website or generic CLI, because they don't know how to **roll dice** or **read files**.

Currently, there are two ways to play:

## Option A: Native CLI (Terminal)
**Best for:** Privacy, Speed, Developers.
**Pros:** Lightweight, supports Gemini/Vertex/Ollama/Claude.
**Cons:** Text-only interface.

Run this command:
```bash
./play.sh [options]
```
*   **Options**:
    *   `-platform=[local|slack|discord]` (Default: local)
    *   `-campaign=[name]` (Default: from .env)
*   **Examples**:
    *   `./play.sh` (Runs local default)
    *   `./play.sh -campaign=oneshot` (Runs local 'oneshot')
    *   `./play.sh -platform=discord` (Runs Discord bot)
*   **Controls**:
    *   **Enter**: Submit message.
    *   **Alt+Enter** (or Esc+Enter): Insert new line.
    *   **Ctrl+D**: Quit.
*   **Requirements**: 
    *   If using Local LLM (Ollama), you **MUST** use a model that supports Tool Calling (e.g. `llama3.1` or `gemma2`). Base `llama3` will fail.
    *   Set `LOCAL_MODEL_NAME=llama3.1` in your `.env`.

---

## Option B: Claude Desktop (GUI)
**Best for:** Nice UI, Visuals.
**Pros:** Clean interface, supports "Project" organization.
**Cons:** Requires `Claude Desktop` app (Mac/Windows only).

This works because Claude Desktop is an **MCP Client**. It knows how to connect to our local server.

### Setup Instructions
1.  **Install Claude Desktop**: [Download Here](https://claude.ai/download).
2.  **Generate Config**:
    Run our Wizard and choose "Claude Desktop" when asked:
    ```bash
    python3 src/wizard.py
    ```
    *It will generate a `claude_desktop_config.json` file.*

3.  **Install Config**:
    *   **MacOS**: Opening Terminal and run:
        ```bash
        cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
        ```
    *   **Windows**: Copy the file to `%APPDATA%\Claude\claude_desktop_config.json`.

4.  **Restart Claude Desktop**.
    You should see a plug icon 🔌 indicating "DungeonMasterTools" are connected.

5.  **Start Campaign**:
    Copy the text from `campaigns/your_campaign/system_prompt.txt` and paste it into a new chat.

---

## Option C: Discord Client (Online)
**Best for:** Group play, Voice chat, Mobile users.
**Pros:** Polished mobile app, easy file uploads.
**Cons:** Requires `DISCORD_BOT_TOKEN`.

1.  **Invite Bot**: Create an application in the Discord Developer Portal and invite the bot to your server.
2.  **Run**: `python3 src/discord_bot.py`.
3.  **Play**: Tag the bot `@AgenticDM` or DM it directly to start playing.

---

## Option D: Antigravity / Agentic IDEs 🤖
**Best for:** Developers hacking on the bot while playing.
**Pros:** seamless integration with code changes.
**Cons:** Requires an MCP-enabled IDE environment.

If you are working in an environment like **Antigravity** (Google's Agentic IDE) or similar MCP-enabled editors:

1.  **Run the Server**:
    Keep `src/mcp_server.py` running in a terminal tab:
    ```bash
    python3 src/mcp_server.py
    ```
2.  **Connect Tools**:
    Your IDE should detect the running server or allow you to configure it as an MCP Resource/Tool provider.
3.  **Play**:
    Open the `system_prompt.txt` file and ask the IDE's Agent: *"Read this system prompt and let's play D&D."*
    The Agent will automatically see the `roll_dice` and `log_event` tools and use them.

---

## ❓ FAQ

### Why can't I use the `gemini` command or ChatGPT?
Because they do not speak **MCP (Model Context Protocol)**.
*   **The Problem**: They can send text, but they cannot "call" the Python functions on your computer that roll dice or save logs.
*   **The Result**: The AI will hallucinate. It will say "I rolled a 20!" but it made that number up, and nothing was saved.

### When will this change?
Google and OpenAI are working on MCP-like standards. Once the `gemini` CLI supports local tool binding, you will be able to use it directly. Until then, use `src/play.py`.
