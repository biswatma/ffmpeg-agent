import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENROUTER_API_KEY')
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}
data = {
    'model': 'google/gemini-2.0-flash-exp:free',
    'messages': [{'role': 'user', 'content': 'Hello'}]
}

with open('api_test_result.txt', 'w') as f:
    f.write("Testing OpenRouter API connection...\n")
    try:
        response = requests.post('https://openrouter.ai/api/v1/chat/completions', 
                              headers=headers, json=data)
        response.raise_for_status()
        f.write(f"API Response: {response.json()}\n")
    except Exception as e:
        f.write(f"Error: {str(e)}\n")
        if hasattr(e, 'response'):
            f.write(f"Response content: {e.response.text}\n")
