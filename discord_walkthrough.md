# Discord Bot Setup Guide 🤖

Setting up a Discord bot is simpler than Slack, but you need to enable specific "Intents" for it to read messages.

## 1. Create Application
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Click **New Application** (top right).
3.  Name it (e.g., "Agentic DM") and click **Create**.

## 2. Create Bot User
1.  In the left sidebar, click **Bot**.
2.  Descriptive options: You can change the icon and username here.
3.  **Authentication Token**:
    *   Click **Reset Token**.
    *   **COPY THIS TOKEN IMMEDIATELY**. You won't see it again.
    *   Save it in your `.env` file as:
        ```bash
        DISCORD_BOT_TOKEN=MTA...
        ```

## 3. Enable Intents (Crucial!)
Scroll down on the **Bot** page to the **Privileged Gateway Intents** section.
You **MUST** enable:
*   ✅ **Message Content Intent** (Allowed to read messages).
*   ✅ **Server Members Intent** (Optional, but good for future permissions).

*If you don't enable `Message Content Intent`, the bot will see the message exists but the text will be empty.*

## 4. Invite to Server
1.  In the left sidebar, click **OAuth2** -> **URL Generator**.
2.  **Scopes**: Check `bot`.
3.  **Bot Permissions**:
    *   Check `Read Messages/View Channels`.
    *   Check `Send Messages`.
    *   Check `Attach Files` (for image generation).
    *   Check `Read Message History` (for context).
4.  **Copy the Generated URL** at the bottom.
5.  Paste it into your browser, select your server, and click **Authorize**.

## 5. Play!
Run the bot:
```bash
./play.sh -platform=discord
```
Tag the bot `@Agentic DM` to start your adventure.
