# Week-3 Project: Research Desk

This week's goal was to improve upon last week's Research agent. Conversation history was saved and could be resumed later. arXiv paper search and read tools were replaced by custom defined functions using Hugging Face Papers API. This week's project can run from command line in a REPL environment as well as in a textual based TUI environment. 

# Setup

The following external dependencies are needed. Call ` pip install -r requirements.txt ` to install them. 
```
openai
python-dotenv
requests
trafilatura
textual
```
**Note -** The file might contain more packages than needed. This is because I have included all packages needed to run any week's agent. (Week 3 in particular had lesser requirements than last week)

Ensure that Openrouter API key and Serper API key are present in a .env file. Run `python week_3/project/agent.py` to launch REPL environment. Use --tui to launch TUI and --session <session_name> to load an existing session.  

# Features 

- Terminal user interface made using textual module in python
- Uses OpenAI to generate a response and call tools whenever required
- Consists of web fetch and web search, along with Hugging Face API integrated paper search and paper fetch.   
- Saves conversation history to storage and updates research notes 

# My Experience

This week's workload was lighter as compared to last week. I had to implement the paper search and fetch functions and the file editing functions. I defined the functions for file manipulation, web searching and research in different files in tools. I defined some tool related parameters as well as imported everything in `__init__.py`. I imported tools in `agent.py`, which contained Agent class and REPLAgent class. The functions used for TUI were defined in `tui.py`. While working with the agent, I noted that even though I had asked the agent to write to notes in AGENTS.md, it wasn't doing anything. Sometimes it would hallucinate that it had used write_file. I modified the prompt a bit so that it could work. I was satisfied with my build. I look forward to what happens in the upcoming weeks!