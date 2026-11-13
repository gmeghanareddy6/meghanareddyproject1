import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

try:
    # Attempt to list models if supported, or just print a message
    # The new SDK might not have a direct list_models method on client.models
    # But let's try a standard generation with a known model to see if it works
    # Or try to iterate if possible. 
    # Actually, client.models.list() is likely the method.
    for m in client.models.list():
        print(m.name)
except Exception as e:
    print(e)
