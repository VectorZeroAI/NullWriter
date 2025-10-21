# NullWriter
A Autonomus self-checking AI powered novel writer.

# Architecture:

---
This thing heavely relies on Openrouter, so thank
you to them for the existanse of free models there,
they do make my day easier by a lot.
---

When the user presses "start":

First, check if the SQLite is present, if not create it.

Then, use Openrouter API whith a free model to create a high level plan for the Novel.

Then, use Openrouter API whith a free model to create a plan for the next chapter.(load the previous chapter and the High level plan into the LLM and just slap something like: "write a plan for the next chapter")

Then we use Openrouter API whith a free model to create the Chapter. We make it 3 times, whereby each of those is a separated thread, for speed. 
(We load the high level novel plan and the chapter plan and the previous chapter(s) (maximum 5 chapters upload))

Then we use Openrouter API whith a free model to compare the 3 chapters, and create a detailed advansed plan for the best chapter.

Then we use a model to create it.

Then we present it to the user, and delete everything else, exept the high level novel plan and the previous chapters.

---

All the model names are in the config.py, with the API key.

Note that all the code should be in one file.


