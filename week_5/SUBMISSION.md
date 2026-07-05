# Week-5 Project: Improved Agent 

This week's goal was to improve upon last week's Code Scout. I added agent skills and implemented integration with mcp by using config file. I also added research tools and saving of conversation history from week_3. Last week's agent did not run on TUI, this week I have made sure that the agent can run on both REPL as well as TUI. 

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

Ensure that Openrouter API key, Serper API key and Github personal access token are present in a .env file. Run `python week_5/project/agent.py` to launch REPL environment. Use --tui to launch TUI and --session <session_name> to load an existing session.  

Use /mcp list to view mcp servers, /mcp enable <server> to connect to a server and /mcp disable <server> to disconnect while using TUI or REPL.

# Features 

- REPL based environment
- Terminal user interface made using textual module in python
- Can view mcp servers (`/mcp list`) and connect to mcp servers (`/mcp enable`)
- Uses OpenAI to generate a response and call tools whenever required
- Consists of web fetch and web search, along with Hugging Face API integrated paper search and paper fetch.   
- Saves conversation history to storage and updates research notes 
- Can run commands on CLI using `run_command` tool

# My Experience

Firstly, I added the agent from week 4. Then I integrated it with TUI along with also adding web tools and paper search tools. I added three agent skills- commit (which can be used to write clean git commit messages), programming (which is basically what the agent of week 4 did) andresearch (using research tools from week 3). I implemented commit from the instructions of this week. In programming, I used the instructions from week_4, that is, adding a todo file, and marking items as it executed the steps. I implemented a popup explicitly asking for user permission while executing an unknown command in TUI. In research, I ensured that the agent only gives a brief answer and writes details in a separate notes/ directory. I also ensured that it uses web search tools when a deep answer is not required. 

I also implemented mcp connection, for this project, I only added mcp connection to github, but more servers can be added in config.json (along with adding required api keys in .env). This supports 3 mcp commands - list, enable and disable and can be activated with `/mcp <command> <server>` (server is not needed in case of list) in both TUI and REPL. It was a fun experience building a working ai agent from scratch!