import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:
    def __init__(self, model = "openrouter/free"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        self.model = model
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        self.last_response = None
    
    def call_model(self):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )
        self.last_response = response
        return response.choices[0].message.content
    
    def token_usage(self):
        if self.last_response:
            print("\nToken Usage:")
            print(f"Prompt Tokens: {self.last_response.usage.prompt_tokens}")
            print(f"Completion Tokens: {self.last_response.usage.completion_tokens}")
            print(f"Total Tokens: {self.last_response.usage.total_tokens}\n")
        else:
            print("\nNo usage history\n")

    def reset(self):
        self.messages = [self.messages[0]]
        self.last_response = None
        print("\nChat history reset\n")

    def run_chatbot(self):
        print("Chat started. Type 'exit' or 'quit' to quit.\n")
        while True:
            user_input = input("User: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("\nThank you for using the chatbot!")
                break
            if user_input == "/reset":
                self.reset()
                continue
            if user_input == "/tokens":
                self.token_usage()
                continue

            self.messages.append({"role": "user", "content": user_input})
            response = self.call_model()
            self.messages.append({"role": "assistant", "content": response})
            print(f"\nAssistant: {response}\n")
            
        
if __name__ == "__main__":
    agent = ChatAgent()
    agent.run_chatbot()