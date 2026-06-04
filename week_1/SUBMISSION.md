# Build-1:
 I removed the type hints and printed the response object to see its structure, it was a python class, ChatCompletion and looked like this:

```
{
  "id": "gen-1780477922-OEEzf5PcuaGtckZyho55",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": "The capital of Australia is **Canberra**.",
        "refusal": null,
        "role": "assistant",
        "annotations": null,
        "audio": null,
        "function_call": null,
        "tool_calls": null,
        "reasoning": "User asks: \"What is the capital of Australia?\" Answer: Canberra. Provide succinct answer.\n\n",
        "reasoning_details": [
          {
            "type": "reasoning.text",
            "text": "User asks: \"What is the capital of Australia?\" Answer: Canberra. Provide succinct answer.\n\n",
            "format": "unknown",
            "index": 0
          }
        ]
      },
      "native_finish_reason": "stop"
    }
  ],
  "created": 1780477922,
  "model": "nvidia/nemotron-3-super-120b-a12b-20230311:free",
  "object": "chat.completion",
  "service_tier": null,
  "system_fingerprint": null,
  "usage": {
    "completion_tokens": 32,
    "prompt_tokens": 23,
    "total_tokens": 55,
    "completion_tokens_details": {
      "accepted_prediction_tokens": null,
      "audio_tokens": 0,
      "reasoning_tokens": 25,
      "rejected_prediction_tokens": null,
      "image_tokens": 0
    },
    "prompt_tokens_details": {
      "audio_tokens": 0,
      "cached_tokens": 0,
      "cache_write_tokens": 0,
      "video_tokens": 0
    },
    "cost": 0,
    "is_byok": false,
    "cost_details": {
      "upstream_inference_cost": 0,
      "upstream_inference_prompt_cost": 0,
      "upstream_inference_completions_cost": 0
    }
  },
  "provider": "Nvidia"
}
```
 To provide the ai response to our query, we would have to use response.choices, which is an array of dictionaries. To access it I used response.choices[0].message.content. By googling, I found out that we can generate multiple choices while using client.chat.completions.create(). 

 Here, the original deepseek model was not working, so I replaced it with openrouter/free. It uses one of the models from openrouter, so the structure of the response object was not the same everytime. However, they did have response.choices, response.usage which were needed to build the chatbot.

# Build-2:
 Since I had developed somewhat a basic understanding of the working of the response object while working with build1.py, there wasn't much problem with modifying build2.py to create multi-turn chatbot. Each time the user asked a query, I created a dictionary {"role":"user", "content":"user_input"} and appended it to messages. I did not implement buffer management now.

# Chatbot.py (Submission):
 I had implemented the functions call_model, run_chatbot, token_usage earlier, so I first converted them into a python class ChatAgent. I made slight modifications for the code to look cleaner like adding a separate reset function. 

 Now I had to work on the buffer management. I created a buffer_limit parameter of the class and initialised it to 4. Now, I planned to take last 4 exchanges. The total length of messages would be greater than 9 for buffer limit to exceed, as there is also the original system message. I created a copy of responses to be retained (system message and last 2N messages) and responses to be summarised. Then I used call_model() on the lattter for summary. I merged the summary(1 element) with the copy of the retained messages.

 I tried seeing what would happen if I don't use summarize and created a copy of chatbot.py. I took only the last 2N messages and dropped everything else. The model was faster, since we make an additional call while using summarize. However, an obvious drawback was complete lack of knowledge of whatever happened before 2N turns. 