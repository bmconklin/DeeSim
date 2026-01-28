# Discord Bot Setup Guide 🤖

Follow this guide to create your Agentic DM bot application in the Discord Developer Portal and connect it to your server.


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
1.  In the left sidebar, click **OAuth2** and then select **URL Generator** from the submenu.
    *   *Note: Do NOT use the "Installation" or "General" tabs under OAuth2. Those are for public bots.*
2.  **Scopes**: Check `bot`.
3.  **Bot Permissions**:
    *   Check `View Channels`.
    *   Check `Send Messages`.
    *   Check `Attach Files` (for image generation).
    *   Check `Read Message History` (for context).
4.  **Copy the Generated URL** at the bottom.
5.  Paste it into your browser, select your server, and click **Authorize**.

### 🔒 Limiting to One Channel
To stop the bot from replying everywhere:
1.  Enable **Developer Mode** in Discord (User Settings -> Advanced).
2.  Right-click the channel you want and select **Copy Channel ID**.
3.  Add this to your `.env`:
    ```bash
    DISCORD_ALLOWED_CHANNEL_ID=1234567890
    ```
4.  Restart the bot. It will now ignore all other channels (except DMs).

## 5. Play!
Run the bot:
```bash
./play.sh -platform=discord
```
Tag the bot `@Agentic DM` to start your adventure.

## ❓ Troubleshooting

### Error: "Private application cannot have a default authorization link"
If you get this error when trying to save on the **Bot** page:
1.  This happens if you unchecked "Public Bot" but have settings in the **Installation** tab.
2.  **Fix**: Refresh the page to discard changes (if stuck).
3.  Go to the **Installation** tab (left sidebar).
4.  **Uncheck** "Default Authorization Link" or clear any settings there.

## 6. Commands 📜

The following commands are available in any channel where the bot has access. You do not need to tag the bot to use them.

### Player Setup
- **`!iam <Character Name>`**: Link your Discord User ID to a specific character name in the campaign.
    - Example: `!iam Rhogar Brass-Gear`

### Visualization & Media
- **`!visualize <description>`**: ✨ The Magic Button. Asks the DM to vividly describe the scene and then generate an image of it efficiently.
    - Example: `!visualize Rhogar casting lightning`
- **`!visualize`** (No args): Context-Aware Mode. The DM reads the recent chat history, infers the current scene, and generates a visual automatically.
- **`!visualize session`**: 🎞️ Highlight Reel. The DM finds the most epic moment from the entire session history and paints it.
- **`!generate <description>`**: Manual Override. Forces the image generator to run with the exact text provided, bypassing the "Description" phase. Use this if you just want a quick render.
    - Example: `!generate A red dragon on a pile of gold`

### Maintenance
- **`!forget`**: 🧠 Mind Wipe. Removes the last user message and bot response from the memory. Use this if the bot gets stuck in a refusal loop (e.g., "I cannot do that").
- **`!hide`**: Clears any pending image prompts that got stuck.

### Session Management
- **`!wrapup`**: Ends the current session. It uses AI to summarize the logs into a "Previously On..." format and archives the full log text.
- **`!startsession`**: Creates the `session_N+1` folder (e.g., `session_2`), moves the pointer in `current_session.txt`, and seeds the new log with the summary from the previous session.

### Legacy/Debug
- **`!show`**: (Deprecated) Used to show a pending image. Use `!generate` or `!visualize` instead.
- **`!admin`**: (Restricted) Placeholder for future DM-only tools.

