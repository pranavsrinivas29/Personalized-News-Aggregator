import requests
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config

def query_ollama_mistral(prompt: str):
    """Query the Ollama Mistral model API."""
    url = "http://localhost:11434/api/generate"
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": "mistral",
        "prompt": prompt
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    prompt = "Here is a story about llamas eating grass"
    result = query_ollama_mistral(prompt)
    if result:
        print("Response:", result)
    else:
        print("Failed to fetch response from Ollama API.")
