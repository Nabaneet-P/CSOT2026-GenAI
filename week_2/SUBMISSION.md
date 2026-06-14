# Week-2 Project: Research Agent

This week's goal was to make a chatbot on terminal like Perplexity, which is capable of searching the web and research papers to answer queries. It was integrated with custom tools for web search and fetching data and Alphaxiv mcp for getting content from research papers. 

# Setup

The following external dependencies are needed. Call ` pip install -r requirements.txt ` to install them. 
```
openai
python-dotenv
requests
trafilatura
textual
mcp
httpx
```
Ensure that Openrouter API key and Serper API key are present in a .env file. Moreover Alphaxiv authorisation is also required. Run ` python3 week_2/project/ouath.py ` and login to the site to generate .alphaxiv_tokens.json. Then run ` python3 week_2/project/agent.py ` to run the chat agent. 

# Features 

- Terminal user interface made using textual module in python
- Uses OpenAI to generate a response and call tools whenever required
- Consists of web fetch and web search, along with Alphaxiv mcp integrated discover_papers and get_paper_content
- Supports exporting the chat history to a local file so that user can look it up later

# How I built it 

I learnt tool calling using builds 1 and 2. Then I integrated it with a TUI using build 3. Then I implemented mcp and created a server.py file and client.py file which made the tool calling organised. 

For the main project I implemented the local functions smart_fetch and web_search. Then I implemented authorization for using Alphaxiv, and added the functions discover_papers and get_paper_content. Then I tried to integrate everything with textual. However I faced a lot of problems and needed help from Gemini to complete building a working TUI. Finally, I created a separate python programme for authentication, which worked. Then I added key bindings for  exit, clearing history, clearing screen, printing token usage, and saving conversation history to a file. 

# My Design Decisions

As mentioned earlier, one of the major things which I did was separate programmes for authentication and running the main agent. I faced trouble in getting the UI work while authenticating. While testing I had not integrated textual and the oauth credentials were saved in my local storage. After building the UI, everything seemed fine, but I decided to delete the credentials and see what would happen. The UI froze and alphaxiv could not connect to localhost. I tried to fix it but was unable to do so. So I used my code before UI integration to create a separate ouath.py for authorization. 

# Challenges

I was very annoyed while working with custom syntax tools. Some models were using incorrect syntax. A lot of times it hallucinated and generated random text like "A quick brown fox...", effects of ai use, etc. I was relieved when tool calling with openai sdk worked. I had to learn how to use mcp and asynchronous programming. I did not implement split screen TUI and hope to do it next week. 