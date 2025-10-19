# NullWriter
A Autonomus self-checking AI powered novel writer.

#Architecture:

---
This thing heavely relies on Openrouter, so thank
you to them for the existanse of free models there,
they do make my day easier by a lot.
---

This brach is made for the prototype1 /idea 1. 

This idea is to tune the programm into a short story writer.

The main changes are:

Json based storage insdead of SQLite based. 
No chapter based generation, rather a one pass pipeline. 

--- 

# Archtecture

First, create this json: 

~~~~ json

{
  "high_level_description": "",
  "characters": [
    {
      "character": "name",
      "description": "description",
      "character": "character traits"
    }
  ],
  "story_plan": "plan",
  "drafts": [
    {
      "model": "the model",
      "draft": "the draft here"
    }
  ]
  "final": "chapter text",
  "user_instructions": "instruction list, e.g. the prompt"
  
}

~~~~


Then we call the first LLM to create the high level descriptions for the story, based on user instructions, e.g. prompt. 
Then we call an LLM o create characters for the story, and append them into the json list. 
Then we call an LLM to create the story plan. 
Then we call 3 LLMs asyncronosly to create the actual story. 
Then we call an LLM to compare all the drafts.
Then we call the final LLM to finaly create the final story.

*Note that every new bit of information is passed onto the next model as well, meaning that something like user instructions gets passed on to every LLM call.*


We wrap it all into a tinkerer GUI with 2 text fields and a start button, and thats it.
