
from agents.medical_analysis import get_gemini_client

print("Testing Gemini 3.8 Flash...", flush=True)

try:
    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Reply with only the word OK.",
        config={
            "temperature": 0,
            "max_output_tokens": 10,
        },
    )

    print("\nGemini response:", response.text)
    print("\nGEMINI TEST PASSED")

except Exception as error:
    print("\nGEMINI TEST FAILED")
    print("Error type:", type(error).__name__)
    print("Error:", str(error))
