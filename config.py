# config.py

# Insert your OpenRouter API key here
OPENROUTER_API_KEY = "your api key here!"

# Model Configuration
MODELS = {
    "high_level": "qwen/qwen3-235b-a22b:free",
    "characters": "qwen/qwen3-14b:free", 
    "story_plan": "qwen/qwen3-30b-a3b:free",
    "drafts": [                                                        # these are defaults, you may change those.
        "meta-llama/llama-3.3-70b-instruct:free",                    # these are defaults, you may change those.
        "openai/gpt-oss-20b:free",                                    # these are defaults, you may change those.
        "tngtech/deepseek-r1t2-chimera:free"                         # these are defaults, you may change those.
    ],
    "comparison": "google/gemma-3-27b-it:free",
    "final": "arliai/qwq-32b-arliai-rpr-v1:free"
}



# Generation Parameters
MAX_RETRIES = 3
TIMEOUT = 60
