
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import traceback

print("1. Starting...", flush=True)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("2. API key loaded:", bool(api_key), flush=True)

try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=120000)
    )

    print("3. Client created", flush=True)
    print("4. Sending request...", flush=True)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Reply with only the word OK."
    )

    print("5. Response received!", flush=True)
    print(response.text)

except Exception as e:
    print("\nERROR:", repr(e), flush=True)
    traceback.print_exc()
