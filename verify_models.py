import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

candidates = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
]

print("Testing models for availability...")

for model in candidates:
    print(f"\nTesting {model}...")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say 'OK'",
        )
        print(f"✅ SUCCESS! Model: {model}")
        print(f"Response: {response.text}")
        break  # Found one!
    except Exception as e:
        print(f"❌ Failed: {e}")
