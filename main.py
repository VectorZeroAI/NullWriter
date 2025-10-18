import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import asyncio
import threading
from openai import OpenAI
from config import OPENROUTER_API_KEY
import os

class StoryGenerator:
    def __init__(self):
        self.story_data = {
            "high_level_description": "",
            "characters": [],
            "story_plan": "",
            "drafts": [],
            "final": "",
            "user_instructions": ""
        }
        
        # Initialize OpenRouter client
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )

    def call_llm(self, prompt, model="openai/gpt-oss-20b:free"):
        """Make API call to OpenRouter"""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_high_level_description(self, user_instructions):
        """Generate high-level story description"""
        prompt = f"""
        Based on the following user instructions, create a compelling high-level description for a short story:
        
        User Instructions: {user_instructions}
        
        Provide a concise but vivid description that sets the tone, setting, and main conflict.
        """
        return self.call_llm(prompt)

    def generate_characters(self, high_level_description):
        """Generate characters for the story"""
        prompt = f"""
        Based on this story description: {high_level_description}
        
        Create 2-3 main characters for this story. For each character provide:
        - Name
        - Description
        - Character traits
        
        Format your response as a JSON-like structure that can be parsed.
        """
        response = self.call_llm(prompt)
        return response

    def generate_story_plan(self, high_level_description, characters):
        """Generate a detailed story plan"""
        prompt = f"""
        Story Description: {high_level_description}
        Characters: {characters}
        
        Create a detailed story plan with:
        1. Beginning (setup)
        2. Middle (conflict development)
        3. End (resolution)
        
        Make it detailed enough to guide the writing of a compelling short story.
        """
        return self.call_llm(prompt)

    def generate_draft(self, story_data, model):
        """Generate a single story draft"""
        prompt = f"""
        Write a complete short story based on the following:
        
        Story Description: {story_data['high_level_description']}
        Characters: {story_data['characters']}
        Story Plan: {story_data['story_plan']}
        User Instructions: {story_data['user_instructions']}
        
        Write a compelling, complete short story that follows the plan and develops the characters.
        Keep it between 500-800 words.
        """
        draft = self.call_llm(prompt, model)
        return {"model": model, "draft": draft}

    async def generate_drafts_async(self, story_data):
        """Generate multiple drafts asynchronously"""
        models = [
            "anthropic/claude-3-sonnet",
            "google/gemini-pro",
            "meta-llama/llama-3-70b-instruct"
        ]
        
        # Run draft generation concurrently
        loop = asyncio.get_event_loop()
        tasks = []
        for model in models:
            task = loop.run_in_executor(None, self.generate_draft, story_data, model)
            tasks.append(task)
        
        drafts = await asyncio.gather(*tasks)
        return drafts

    def generate_final_story(self, story_data):
        """Generate the final story by synthesizing the best drafts"""
        drafts_text = "\n\n".join([f"Draft from {draft['model']}:\n{draft['draft']}" 
                                 for draft in story_data['drafts']])
        
        prompt = f"""
        You have been given multiple drafts of the same story. Synthesize the best elements 
        from all drafts to create a final, polished version.
        
        Original Instructions: {story_data['user_instructions']}
        Story Plan: {story_data['story_plan']}
        Characters: {story_data['characters']}
        
        Here are the drafts:
        {drafts_text}
        
        Create a final version that:
        1. Maintains the original vision and instructions
        2. Incorporates the best writing from all drafts
        3. Has consistent characterization
        4. Flows smoothly from beginning to end
        5. Is between 600-900 words
        
        Write the final story:
        """
        return self.call_llm(prompt)

    def parse_characters(self, characters_text):
        """Parse character information from LLM response"""
        # Simple parsing - in a real implementation, you might want more robust parsing
        lines = characters_text.split('\n')
        characters = []
        current_char = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith('name:'):
                if current_char:
                    characters.append(current_char)
                current_char = {'character': line.split(':', 1)[1].strip()}
            elif line.lower().startswith('description:'):
                current_char['description'] = line.split(':', 1)[1].strip()
            elif 'trait' in line.lower():
                current_char['character traits'] = line.split(':', 1)[1].strip()
        
        if current_char:
            characters.append(current_char)
            
        return characters

class StoryGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Autonomous Story Generator")
        self.root.geometry("800x600")
        
        self.generator = StoryGenerator()
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Instructions label
        ttk.Label(main_frame, text="Enter your story instructions:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Instructions text area
        self.instructions_text = scrolledtext.ScrolledText(main_frame, height=5, width=80)
        self.instructions_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Start button
        self.start_button = ttk.Button(main_frame, text="Generate Story", command=self.start_generation)
        self.start_button.grid(row=2, column=0, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        
        # Output label
        ttk.Label(main_frame, text="Generated Story:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(main_frame, height=20, width=80)
        self.output_text.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()
        
    def update_output(self, text):
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(1.0, text)
        self.root.update()
        
    def append_output(self, text):
        self.output_text.insert(tk.END, text + "\n\n")
        self.root.update()
        
    def start_generation(self):
        # Disable button and start progress bar
        self.start_button.config(state='disabled')
        self.progress.start()
        
        # Start generation in a separate thread
        thread = threading.Thread(target=self.generate_story_thread)
        thread.daemon = True
        thread.start()
        
    def generate_story_thread(self):
        try:
            # Get user instructions
            instructions = self.instructions_text.get(1.0, tk.END).strip()
            self.generator.story_data["user_instructions"] = instructions
            
            self.update_status("Generating high-level description...")
            high_level_desc = self.generator.generate_high_level_description(instructions)
            self.generator.story_data["high_level_description"] = high_level_desc
            self.append_output("=== HIGH LEVEL DESCRIPTION ===\n" + high_level_desc)
            
            self.update_status("Generating characters...")
            characters_text = self.generator.generate_characters(high_level_desc)
            characters = self.generator.parse_characters(characters_text)
            self.generator.story_data["characters"] = characters
            self.append_output("=== CHARACTERS ===\n" + characters_text)
            
            self.update_status("Generating story plan...")
            story_plan = self.generator.generate_story_plan(high_level_desc, characters)
            self.generator.story_data["story_plan"] = story_plan
            self.append_output("=== STORY PLAN ===\n" + story_plan)
            
            self.update_status("Generating drafts (this may take a while)...")
            # Run async drafts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            drafts = loop.run_until_complete(
                self.generator.generate_drafts_async(self.generator.story_data)
            )
            self.generator.story_data["drafts"] = drafts
            
            for i, draft in enumerate(drafts, 1):
                self.append_output(f"=== DRAFT {i} ({draft['model']}) ===\n" + draft['draft'])
            
            self.update_status("Generating final story...")
            final_story = self.generator.generate_final_story(self.generator.story_data)
            self.generator.story_data["final"] = final_story
            self.append_output("=== FINAL STORY ===\n" + final_story)
            
            # Save to JSON file
            with open("generated_story.json", "w") as f:
                json.dump(self.generator.story_data, f, indent=2)
            
            self.update_status("Complete! Story saved to generated_story.json")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.append_output(f"ERROR: {str(e)}")
        finally:
            # Re-enable button and stop progress bar
            self.progress.stop()
            self.start_button.config(state='normal')

def main():
    root = tk.Tk()
    app = StoryGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
