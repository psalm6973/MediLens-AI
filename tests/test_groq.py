
import os

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Get Groq API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

# Initialize Groq client
client = Groq(api_key=api_key)

# Send a test request
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Explain what a Complete Blood Count (CBC) report is in 3 simple sentences."
        }
    ],
    temperature=0.3,
    max_tokens=200,
)

# Display response
print("\n========== GROQ API TEST ==========\n")
print(response.choices[0].message.content)
print("\n==================================")
