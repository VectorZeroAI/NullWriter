import os
import sqlite3
import json
import threading
import requests
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from config import OPENROUTER_API_KEY, HIGH_LEVEL_MODEL, CHAPTER_PLAN_MODEL, DRAFT_MODELS, COMPARISON_MODEL, FINAL_MODEL

DB_NAME = "zerowriter.db"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://zerowriter.app",
    "X-Title": "ZeroWriter"
}

API_URL = "https://openrouter.ai/api/v1/chat/completions"

class ZeroWriterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZeroWriter - AI Story Generator")
        self.root.geometry("1000x700")
        
        # Initialize database
        init_db()
        
        # Create GUI elements
        self.create_widgets()
        self.load_existing_data()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="ZeroWriter AI Story Generator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))
        
        # Action buttons
        ttk.Button(button_frame, text="Generate New Story", 
                  command=self.generate_new_story).pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Generate Next Chapter", 
                  command=self.generate_next_chapter).pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Refresh Display", 
                  command=self.load_existing_data).pack(fill=tk.X, pady=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(button_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(button_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, pady=5)
        
        # Notebook for different views
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Story Plan tab
        plan_frame = ttk.Frame(notebook, padding="5")
        notebook.add(plan_frame, text="Story Plan")
        
        self.plan_text = scrolledtext.ScrolledText(plan_frame, wrap=tk.WORD, width=80, height=20)
        self.plan_text.pack(fill=tk.BOTH, expand=True)
        
        # Chapters tab
        chapters_frame = ttk.Frame(notebook, padding="5")
        notebook.add(chapters_frame, text="Chapters")
        
        # Chapters list and content
        chapters_list_frame = ttk.Frame(chapters_frame)
        chapters_list_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(chapters_list_frame, text="Chapters:").pack(side=tk.LEFT)
        self.chapters_listbox = tk.Listbox(chapters_list_frame, height=8)
        self.chapters_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.chapters_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        self.chapter_content_text = scrolledtext.ScrolledText(chapters_frame, wrap=tk.WORD, width=80, height=15)
        self.chapter_content_text.pack(fill=tk.BOTH, expand=True)
        
        # Raw Data tab
        raw_frame = ttk.Frame(notebook, padding="5")
        notebook.add(raw_frame, text="Raw Data")
        
        self.raw_text = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD, width=80, height=20)
        self.raw_text.pack(fill=tk.BOTH, expand=True)
        
    def set_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def start_progress(self):
        self.progress.start()
        
    def stop_progress(self):
        self.progress.stop()
        
    def generate_new_story(self):
        def worker():
            self.start_progress()
            self.set_status("Generating high-level story plan...")
            try:
                plan = generate_high_level_plan()
                self.root.after(0, lambda: self.on_story_generated(plan))
            except Exception as e:
                self.root.after(0, lambda: self.on_error(f"Error generating story: {str(e)}"))
                
        threading.Thread(target=worker, daemon=True).start()
        
    def on_story_generated(self, plan):
        self.stop_progress()
        self.set_status("Story plan generated successfully!")
        self.load_existing_data()
        messagebox.showinfo("Success", "New story plan has been generated!")
        
    def generate_next_chapter(self):
        # Check if we have a story plan first
        if not get_high_level_plan():
            messagebox.showwarning("Warning", "Please generate a story plan first!")
            return
            
        def worker():
            self.start_progress()
            try:
                # Step 1: Get high level plan and previous chapters
                self.set_status("Getting story context...")
                high_plan = get_high_level_plan()
                prev_chapters = get_previous_chapters()
                
                # Step 2: Generate chapter plan
                self.set_status("Generating chapter plan...")
                chapter_plan = generate_chapter_plan(high_plan, prev_chapters)
                chapter_num = get_next_chapter_num()
                
                # Step 3: Write drafts
                self.set_status("Writing drafts...")
                for i, model in enumerate(DRAFT_MODELS):
                    self.set_status(f"Writing draft {i+1}/{len(DRAFT_MODELS)}...")
                    write_draft(model, chapter_num, high_plan, chapter_plan, prev_chapters)
                
                # Step 4: Compare and create detailed plan
                self.set_status("Comparing drafts...")
                detailed_plan = compare_drafts_and_create_plan(chapter_num)
                
                # Step 5: Write final chapter
                self.set_status("Writing final chapter...")
                final_content = write_final_chapter(chapter_num, detailed_plan, high_plan, prev_chapters)
                
                # Step 6: Cleanup
                cleanup_chapter(chapter_num)
                
                self.root.after(0, lambda: self.on_chapter_generated(final_content))
                
            except Exception as e:
                self.root.after(0, lambda: self.on_error(f"Error generating chapter: {str(e)}"))
                
        threading.Thread(target=worker, daemon=True).start()
        
    def on_chapter_generated(self, content):
        self.stop_progress()
        self.set_status("Chapter generated successfully!")
        self.load_existing_data()
        messagebox.showinfo("Success", f"New chapter has been generated!\n\nPreview: {content[:200]}...")
        
    def on_error(self, error_message):
        self.stop_progress()
        self.set_status("Error occurred")
        messagebox.showerror("Error", error_message)
        
    def load_existing_data(self):
        try:
            # Load story plan
            plan = get_high_level_plan()
            self.plan_text.delete(1.0, tk.END)
            if plan:
                self.plan_text.insert(1.0, plan)
            else:
                self.plan_text.insert(1.0, "No story plan generated yet. Click 'Generate New Story' to start.")
                
            # Load chapters list
            self.chapters_listbox.delete(0, tk.END)
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT chapter_num, content FROM chapters WHERE type='final' ORDER BY chapter_num")
            chapters = cursor.fetchall()
            conn.close()
            
            for chapter_num, content in chapters:
                preview = content[:50] + "..." if len(content) > 50 else content
                self.chapters_listbox.insert(tk.END, f"Chapter {chapter_num}: {preview}")
                
            # Load raw data
            self.load_raw_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading data: {str(e)}")
            
    def on_chapter_select(self, event):
        selection = self.chapters_listbox.curselection()
        if not selection:
            return
            
        selected_text = self.chapters_listbox.get(selection[0])
        chapter_num = int(selected_text.split(":")[0].split(" ")[1])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM chapters WHERE chapter_num=? AND type='final'", (chapter_num,))
        result = cursor.fetchone()
        conn.close()
        
        self.chapter_content_text.delete(1.0, tk.END)
        if result:
            self.chapter_content_text.insert(1.0, result[0])
            
    def load_raw_data(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get all data
        cursor.execute("SELECT * FROM novel_plan ORDER BY id DESC")
        plans = cursor.fetchall()
        
        cursor.execute("SELECT * FROM chapters ORDER BY chapter_num, type")
        chapters = cursor.fetchall()
        
        conn.close()
        
        raw_text = "=== NOVEL PLANS ===\n\n"
        for plan_id, content in plans:
            raw_text += f"Plan ID: {plan_id}\n{content}\n{'-'*50}\n\n"
            
        raw_text += "\n=== CHAPTERS ===\n\n"
        for chap_id, chapter_num, chap_type, model, content in chapters:
            raw_text += f"Chapter {chapter_num} - {chap_type} ({model})\n{content}\n{'-'*50}\n\n"
            
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.insert(1.0, raw_text)

# Your existing functions (keep them as they are)
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
    """
    )
    cursor.execute("""
        CREATE TABLE chapters (
            id INTEGER PRIMARY KEY,
            chapter_num INTEGER,
            type TEXT, -- plan, draft, final
            model TEXT,
            content TEXT
        )
    """
    )
    conn.commit()
    conn.close()

def api_call(model, prompt):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    for i in range(3):
        try:
            res = requests.post(API_URL, headers=HEADERS, json=body, timeout=90)
            if res.status_code != 200:
                print(f"API Error {res.status_code}: {res.text[:500]}")
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Attempt {i+1}/3 failed: {e}")
            time.sleep(3)
    return ""

def get_next_chapter_num():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(chapter_num) FROM chapters WHERE type='final'")
    result = cursor.fetchone()
    conn.close()
    return (result[0] or 0) + 1

def get_previous_chapters(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT content FROM chapters WHERE type='final' ORDER BY chapter_num DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return "\n\n".join(row[0] for row in reversed(rows))

def save_chapter(chapter_num, type_, model, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chapters (chapter_num, type, model, content) VALUES (?, ?, ?, ?)",
        (chapter_num, type_, model, content)
    )
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
    prompt = (
        f"Novel Plan:\n{high_plan}\n\n"
        f"Previous Chapters:\n{prev_chapters}\n\n"
        "Write a structured plan for the next chapter."
    )
    plan = api_call(CHAPTER_PLAN_MODEL, prompt)
    save_chapter(get_next_chapter_num(), "plan", CHAPTER_PLAN_MODEL, plan)
    return plan

def write_draft(model, chapter_num, high_plan, chap_plan, prev_chaps):
    prompt = (
        f"Novel Plan:\n{high_plan}\n\n"
        f"Chapter Plan:\n{chap_plan}\n\n"
        f"Previous Chapters:\n{prev_chaps}\n\n"
        "Now write the next chapter in detail."
    )
    content = api_call(model, prompt)
    save_chapter(chapter_num, "draft", model, content)

def compare_drafts_and_create_plan(chapter_num):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT content FROM chapters WHERE chapter_num=? AND type='draft' ORDER BY id ASC",
        (chapter_num,)
    )
    drafts = [row[0] for row in cursor.fetchall()]
    conn.close()

    if len(drafts) < len(DRAFT_MODELS):
        return ""

    prompt = (
        "Compare the following draft versions and write a plan that selects the best ideas, tone, pacing, and structure from all.\n"
        f"\n--- Drafts ---\n" + "\n---\n".join(drafts)
    )
    detailed_plan = api_call(COMPARISON_MODEL, prompt)
    save_chapter(chapter_num, "plan", COMPARISON_MODEL, detailed_plan)
    return detailed_plan

def write_final_chapter(chapter_num, detailed_plan, high_plan, prev_chaps):
    prompt = (
        f"Novel Plan:\n{high_plan}\n\n"
        f"Detailed Plan for Chapter {chapter_num}:\n{detailed_plan}\n\n"
        f"Previous Chapters:\n{prev_chaps}\n\n"
        "Now write the final version of the chapter."
    )
    content = api_call(FINAL_MODEL, prompt)
    save_chapter(chapter_num, "final", FINAL_MODEL, content)
    return content

def cleanup_chapter(chapter_num):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM chapters WHERE chapter_num=? AND type IN ('draft','plan')",
        (chapter_num,)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ZeroWriterGUI(root)
    root.mainloop()
