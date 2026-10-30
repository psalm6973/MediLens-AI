
from dotenv import load_dotenv
from google import genai
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: Gemini API key not found in .env")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents="Reply with exactly: MediLens AI connection successful!"
        )

        print("Gemini connection successful!")
        print("Response:", response.text)

    except Exception as error:
        print("Gemini connection failed.")
        print("Error:", error)
