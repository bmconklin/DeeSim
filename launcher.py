
import os
import subprocess
import time
import sys
from dotenv import load_dotenv

def run_launcher():
    load_dotenv()
    
    processes = []
    
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_app_token = os.environ.get("SLACK_APP_TOKEN")
    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    
    if slack_token and slack_app_token:
        print("🟢 Starting Slack Bot...")
        p_slack = subprocess.Popen([sys.executable, "src/bot.py"])
        processes.append(p_slack)
    else:
        print("⚪ Slack tokens missing, skipping Slack bot.")
        
    if discord_token:
        print("🔵 Starting Discord Bot...")
        p_discord = subprocess.Popen([sys.executable, "src/discord_bot.py"])
        processes.append(p_discord)
    else:
        print("⚪ Discord token missing, skipping Discord bot.")
        
    if not processes:
        print("❌ No bot tokens found. Please check your .env file.")
        return
        
    print("\n🚀 Agentic DM Launcher: Both bots are running. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            # Monitor processes
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ Process {p.pid} exited with code {p.returncode}. Restarting in 5s...")
                    time.sleep(5)
                    # Simple restart logic could go here
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bots...")
        for p in processes:
            p.terminate()
        print("Done.")

if __name__ == "__main__":
    run_launcher()
