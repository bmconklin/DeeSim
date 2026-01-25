import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Skipping test: No GOOGLE_API_KEY")
    exit(0)

client = genai.Client(api_key=api_key)
chat = client.chats.create(model="gemini-2.0-flash-exp")

print("Chat Object Type:", type(chat))
print("Dir(chat):", dir(chat))

try:
    print("History attr:", chat.history)
except Exception as e:
    print("Chat.history failed:", e)

# send a message to populate history
response = chat.send_message("Hello")
print("Context after message:", chat._context if hasattr(chat, "_context") else "No _context")
