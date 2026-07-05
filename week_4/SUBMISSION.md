# Week-4 Project: Code Scout

The goal of this week was to create a CLI coding agent which can investigate and fix issues in a real, unfamiliar codebase. It can search, read, edit and run tests by working through a todo list until the fix is actually verified. 

# Setup

The following external dependencies are needed. Call ` pip install -r requirements.txt ` to install them. 
```
openai
python-dotenv
```
**Note -** The file might contain more packages than needed. This is because I have included all packages needed to run any week's agent.

Ensure that Openrouter API key is present in a .env file. Run `python week_4/project/agent.py` to launch REPL environment. Use --session <session_name> to load an existing session.  

# Features 

- REPL based environment
- Uses OpenAI to generate a response and call tools whenever required
- Saves conversation history to storage 
- Can run commands on CLI using `run_command` tool

# My Experience

I built the command execution tool by creating run_command and also added classify_command which can check if a given command is safe or not. Then I created the tools for making and verifying the entries of a todo list. I created the list_definitions tool using python's ast library. Then, I imported write_file and edit_file from week 3. I observed that grep was slightly unreliable and added custom tools from week 3. I faced another problem, the daily token limits were getting exhausted rather quickly. I implemented time.sleep() for some pause between each iteration of an api call. I made some minor changes to ensure that the token usage is minimised. I did not implement TUI this week as for most of the time, the tokens were getting used in a single session, so I could not test it. I observed how creating a todo list and working based on it improved the efficiency of the agent. 