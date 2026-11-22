

import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: API key not found in .env")

else:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=120000)
    )

    for attempt in range(1, 4):
        try:
            print(f"Connecting to Gemini... Attempt {attempt}/3")

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents="Reply briefly: Your Personal Finance Advisor Bot is connected."
            )

            print("\nSUCCESS! Gemini is connected.")
            print(response.text)
            break

        except Exception as e:
            print("Connection issue:", e)

            if attempt < 3:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("\nGemini is currently unavailable.")
                print("We will use a local demo fallback.")
