# config.py

# 🚨 Insert your OpenRouter API key here
OPENROUTER_API_KEY = "your-api-key"

# ===============================
# ZeroWriter: Model Assignments
# ===============================

# Step 1: High-Level Novel Plan
HIGH_LEVEL_MODEL = "meta-llama/llama-4-maverick:free"

# Step 2: Chapter Plan
CHAPTER_PLAN_MODEL = "mistralai/mistral-small-3.1-24b-instruct:free"

# Step 3: Draft Generation (Parallel Threads)
DRAFT_MODELS = [
    "deepseek/deepseek-chat-v3-0324:free",     # narrative / dialogue-rich
    "qwen/qwen3-coder:free",                   # structured / coherent logic
    "tngtech/deepseek-r1t2-chimera:free"       # speed + hybrid output
]

# Step 4: Comparison & Synthesis of Best Plan
COMPARISON_MODEL = "deepseek/deepseek-r1-zero:free"

# Step 5: Final Chapter Writer
FINAL_MODEL = "google/gemini-2.5-pro-exp-03-25:free"