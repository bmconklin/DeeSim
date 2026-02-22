
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    exit(1)

client = genai.Client(api_key=api_key)

try:
    print("Listing models...")
    for m in client.models.list(config={"page_size": 100}):
        # Print everything to be sure
        print(f"Model: {m.name}")
        try:
            print(f"  - Display Name: {m.display_name}")
        except Exception:
            pass
        try:
            print(f"  - Supported Methods: {m.supported_generation_methods}")
        except Exception:
            pass
        print("-" * 20)
            
except Exception as e:
    print(f"Error listing models: {e}")
