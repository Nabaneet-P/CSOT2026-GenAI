import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def run_chatbot():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    last_response = None

    print("Chat started. Type 'exit' or 'quit' to quit.\n")

    while True:
        user_input = input("User: ").strip()
        
        if user_input.lower() in ["exit", "quit"]:
            print("\nThank you for using the chatbot!")
            break
        if user_input == "/reset":
            messages = messages[0]
            print("\nChat history reset\n")
            continue
        if user_input == "/tokens":
            if (last_response):
                print("\nToken Usage:")
                print(f"Prompt Tokens: {last_response.usage.prompt_tokens}")
                print(f"Completion Tokens: {last_response.usage.completion_tokens}")
                print(f"Total Tokens: {last_response.usage.total_tokens}\n")
            else:
                print("\nNo usage history\n")
            continue

        messages.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
        )
        last_response = response
        agent_response = response.choices[0].message.content
        messages.append({"role": "assistant", "content": agent_response})

        print(f"\nAssistant: {agent_response}\n")
        
if __name__ == "__main__":
    run_chatbot()
