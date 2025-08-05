import os
import sqlite3
import json
import threading
import requests
import time
from config import OPENROUTER_API_KEY, HIGH_LEVEL_MODEL, CHAPTER_PLAN_MODEL, DRAFT_MODELS, COMPARISON_MODEL, FINAL_MODEL

DB_NAME = "zerowriter.db"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ChatGPT said: "May your code be elegant, your bugs be few, and your creativity boundless."

def init_db():
    if os.path.exists(DB_NAME):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE novel_plan (
            id INTEGER PRIMARY KEY, 
            content TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE chapters (
            id INTEGER PRIMARY KEY,
            chapter_num INTEGER,
            type TEXT, -- plan, draft, final
            model TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def api_call(model, prompt):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    for _ in range(3):
        try:
            res = requests.post(API_URL, headers=HEADERS, json=body, timeout=60)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("API error:", e)
            time.sleep(2)
    return ""

def get_previous_chapters(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM chapters WHERE type='final' ORDER BY chapter_num DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return "\n\n".join(row[0] for row in reversed(rows))

def save_chapter(chapter_num, type_, model, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chapters (chapter_num, type, model, content)
        VALUES (?, ?, ?, ?)
    """, (chapter_num, type_, model, content))
    conn.commit()
    conn.close()

def generate_high_level_plan():
    prompt = "Write a high-level plan for an original novel. Include characters, setting, and major plot arcs."
    result = api_call(HIGH_LEVEL_MODEL, prompt)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO novel_plan (content) VALUES (?)", (result,))
    conn.commit()
    conn.close()
    return result

def get_high_level_plan():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM novel_plan ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def generate_chapter_plan(high_plan, prev_chapters):
    prompt = f"Novel Plan:\n{high_plan}\n\nPrevious Chapters:\n{prev_chapters}\n\nWrite a structured plan for the next chapter."
    return api_call(CHAPTER_PLAN_MODEL, prompt)

def write_draft(model, chapter_num, high_plan, chap_plan, prev_chaps):
    prompt = f"Novel Plan:\n{high_plan}\n\nChapter Plan:\n{chap_plan}\n\nPrevious Chapters:\n{prev_chaps}\n\nNow write the next chapter in detail."
    content = api_call(model, prompt)
    save_chapter(chapter_num, "draft", model, content)

def compare_drafts_and_create_plan(chapter_num):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM chapters WHERE chapter_num=? AND type='draft'", (chapter_num,))
    drafts = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if len(drafts) < 3:
        return ""

    prompt = ("Compare the following 3 versions of the same chapter and write a plan that selects the best ideas, tone, pacing, and structure from all.\n"
              f"\n--- Draft 1 ---\n{drafts[0]}\n\n--- Draft 2 ---\n{drafts[1]}\n\n--- Draft 3 ---\n{drafts[2]}\n")
    return api_call(COMPARISON_MODEL, prompt)

def write_final_chapter(chapter_num, detailed_plan, high_plan, prev_chaps):
    prompt = f"Novel Plan:\n{high_plan}\n\nDetailed Plan for Chapter {chapter_num}:\n{detailed_plan}\n\nPrevious Chapters:\n{prev_chaps}\n\nNow write the final version of the chapter."
    content = api_call(FINAL_MODEL, prompt)
    save_chapter(chapter_num, "final", FINAL_MODEL, content)
    return content

def cleanup_chapter(chapter_num):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chapters WHERE chapter_num=? AND type='draft'", (chapter_num,))
    cursor.execute("DELETE FROM chapters WHERE chapter_num=? AND type='plan'", (chapter_num,))
    conn.commit()
    conn.close()

def run_zero_writer():
    init_db()

    high_plan = get_high_level_plan()
    if not high_plan:
        print("Generating high-level novel plan...")
        high_plan = generate_high_level_plan()

    prev_chaps = get_previous_chapters()
    chapter_num = len(prev_chaps.split("Chapter "))  # crude count

    print("Generating chapter plan...")
    chap_plan = generate_chapter_plan(high_plan, prev_chaps)
    save_chapter(chapter_num, "plan", CHAPTER_PLAN_MODEL, chap_plan)

    print("Writing 3 draft versions in parallel...")
    threads = []
    for model in DRAFT_MODELS:
        t = threading.Thread(target=write_draft, args=(model, chapter_num, high_plan, chap_plan, prev_chaps))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    print("Comparing drafts and generating a refined plan...")
    detailed_plan = compare_drafts_and_create_plan(chapter_num)

    print("Writing final chapter...")
    final_text = write_final_chapter(chapter_num, detailed_plan, high_plan, prev_chaps)

    print("\n\n--- FINAL CHAPTER ---\n")
    print(final_text)

    cleanup_chapter(chapter_num)

if __name__ == "__main__":
    input("Press Enter to START novel generation...\n")
    run_zero_writer()
