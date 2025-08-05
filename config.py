# config.py
OPENROUTER_API_KEY = "your-api-key"

HIGH_LEVEL_MODEL = "mistralai/mixtral-8x7b-instruct:free"
CHAPTER_PLAN_MODEL = "mistralai/mixtral-8x7b-instruct:free"
DRAFT_MODELS = [
    "openchat/openchat-7b:free",
    "mistralai/mixtral-8x7b-instruct:free",
    "togethercomputer/llama-2-13b-chat:free"
]
COMPARISON_MODEL = "deepseek/deepseek-coder:free"
FINAL_MODEL = "togethercomputer/llama-2-13b-chat:free"