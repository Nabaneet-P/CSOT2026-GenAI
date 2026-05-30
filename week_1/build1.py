import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def call_model(prompt: str) -> str:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    print("Enter your query")
    prompt=input()
    print(call_model(prompt), flush=True)
