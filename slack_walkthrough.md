# Slackbot Setup Guide

This guide allows you to run your Agentic DM as a Slack bot user (`@DungeonMaster`) for free.

## Step 1: Create a Slack App
1. Go to [api.slack.com/apps](https://api.slack.com/apps).
2. Click **Create New App**.
3. Choose **From scratch**.
4. Name it **DeeSim** (or whatever you prefer) and select your workspace.

## Step 2: Enable Socket Mode (App Token)
1. In the sidebar, click **Socket Mode**.
2. Toggle **Enable Socket Mode**.
3. Generate an App-level Token:
   - Name: `SocketToken`
   - Scope: `connections:write`
   - Click **Generate**.
4. **Copy the `xapp-...` token**. This is your `SLACK_APP_TOKEN`.

## Step 3: Bot Permissions (Bot Token)
1. In the sidebar, click **OAuth & Permissions**.
2. Scroll down to **Scopes** -> **Bot Token Scopes**.
3. Add the following scopes:
   - `app_mentions:read` (Hear when you tag it)
   - `chat:write` (Speak back)
   - `channels:history` (Read context if needed)
   - `files:read` (Download images/maps)
   - `files:write` (Upload generated images)
4. Scroll up and click **Install to Workspace**.
5. **Copy the `xoxb-...` token**. This is your `SLACK_BOT_TOKEN`.

## Step 4: Event Subscriptions
1. In the sidebar, click **Event Subscriptions**.
2. Toggle **Enable Events**.
3. Under **Subscribe to bot events**, add:
   - `app_mention` (When tagged)
   - `message.channels` (Passive listening/context buffer)
4. Click **Save Changes** (bottom right).
5. (If prompted to reinstall app at the top, do it).

## Step 5: Google API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Create an API Key.
3. This is your `GOOGLE_API_KEY`.

## Step 6: Local Setup
1. Create a file named `.env` in the `gemini_dm` folder.
2. Add your keys:
   ```env
   SLACK_APP_TOKEN=xapp-1-xxxxxxxx...
   SLACK_BOT_TOKEN=xoxb-xxxxxxxx...
   GOOGLE_API_KEY=AIzaSy...
   DM_CAMPAIGN_ROOT=/absolute/path/to/gemini_dm/campaigns/new_adventure
   ```
   *(Note: Set `DM_CAMPAIGN_ROOT` to your specific campaign folder so the bot knows which game to load. You can find this path in `start.sh` output or by running `pwd` in your campaign folder.)*

3. Run the setup script:
   ```bash
   ./setup_slack.sh
   ```

4. Start the bot:
   ```bash
   python3 src/bot.py
   ```

## How to Play
1. Go to Slack.
2. Create a channel (e.g. `#dnd-session`).
3. Invite the bot: `/invite @DeeSim`.
4. Say hello: `@DeeSim Let's start the game!`
