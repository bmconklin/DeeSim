import os
import sys
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("No API Key found")
    sys.exit(1)

client = genai.Client(api_key=api_key)

print("Attempting to generate a test image with Imagen 4...")
try:
    response = client.models.generate_images(
        model='imagen-4.0-fast-generate-001',
        prompt='A chill dungeon master dice roll, pixel art style, 8bit',
        config=types.GenerateImagesConfig(
            number_of_images=1
        )
    )
    if response.generated_images:
        print("✅ Success! Image generated.")
    else:
        print("❌ No images returned.")
        
except Exception as e:
    print(f"❌ Error: {e}")
