import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import asyncio
import threading
from openai import OpenAI
import os
import config

# Import Gemini if enabled
if config.USE_GEMINI:
    import google.generativeai as genai

class StoryGenerator:
    def __init__(self):
        self.story_data = {
            "high_level_description": "",
            "characters": [],
            "story_plan": "",
            "drafts": [],
            "draft_comparison": "",
            "final": "",
            "user_instructions": ""
        }

        # Initialize API clients based on configuration
        if config.USE_GEMINI:
            # Configure Gemini
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.gemini_client = genai
        else:
            # Initialize OpenRouter client
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.OPENROUTER_API_KEY
            )

    def call_llm(self, prompt, model=None):
        """Make API call to either Gemini or OpenRouter based on configuration"""
        if config.USE_GEMINI:
            return self.call_gemini(prompt, model)
        else:
            return self.call_openrouter(prompt, model)

    def call_openrouter(self, prompt, model="anthropic/claude-3-sonnet"):
        """Make API call to OpenRouter"""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def call_gemini(self, prompt, model=None):
        """Make API call to Gemini"""
        try:
            if model is None:
                model = config.MODELS.get("high_level", "gemini-pro")
            
            # Use the appropriate Gemini model
            gemini_model = self.gemini_client.GenerativeModel(model)
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def get_model_for_stage(self, stage):
        """Get the appropriate model for a given generation stage"""
        if config.USE_GEMINI:
            # For Gemini, we can use the same model for all stages or configure differently
            return config.MODELS.get(stage, "gemini-pro")
        else:
            return config.MODELS.get(stage, "anthropic/claude-3-sonnet")

    def generate_high_level_description(self, user_instructions):
        """Generate high-level story description"""
        prompt = f"""
        Based on the following user instructions, create a compelling high-level description for a short story:
        
        USER INSTRUCTIONS: {user_instructions}
        
        Provide a concise but vivid description that sets the tone, setting, and main conflict.
        Keep the user's original vision clearly in mind while creating this description.
        
        High-level description:
        """
        model = self.get_model_for_stage("high_level")
        return self.call_llm(prompt, model)

    def generate_characters(self, user_instructions, high_level_description):
        """Generate characters for the story"""
        prompt = f"""
        Based on these story elements, create 2-3 main characters for this story:
        
        USER INSTRUCTIONS: {user_instructions}
        STORY DESCRIPTION: {high_level_description}
        
        For each character provide:
        - Name
        - Description (appearance, background, role)
        - Character traits (personality, motivations, flaws)
        
        Ensure the characters align with the user's original instructions.
        Format your response as a JSON-like structure that can be parsed.
        
        Characters:
        """
        model = self.get_model_for_stage("characters")
        response = self.call_llm(prompt, model)
        return response

    def generate_story_plan(self, user_instructions, high_level_description, characters):
        """Generate a detailed story plan"""
        prompt = f"""
        Create a detailed story plan based on these elements:
        
        USER INSTRUCTIONS: {user_instructions}
        STORY DESCRIPTION: {high_level_description}
        CHARACTERS: {characters}
        
        Create a detailed story plan with:
        1. Beginning (setup, character introduction, initial situation)
        2. Middle (conflict development, character challenges, rising action)
        3. End (climax, resolution, character growth)
        
        Make sure the plan stays true to the user's original instructions.
        Make it detailed enough to guide the writing of a compelling short story.
        
        Story Plan:
        """
        model = self.get_model_for_stage("story_plan")
        return self.call_llm(prompt, model)

    def generate_draft(self, user_instructions, story_data, model):
        """Generate a single story draft"""
        prompt = f"""
        Write a complete short story based on the following elements:
        
        ORIGINAL USER INSTRUCTIONS: {user_instructions}
        STORY DESCRIPTION: {story_data['high_level_description']}
        CHARACTERS: {story_data['characters']}
        STORY PLAN: {story_data['story_plan']}
        
        Important: Stay faithful to the user's original instructions above.
        
        Write a compelling, complete short story that:
        - Follows the story plan
        - Develops the characters according to their descriptions
        - Maintains consistency with the high-level description
        - Adheres to the user's original vision
        - Is between 500-800 words
        
        Short Story:
        """
        draft = self.call_llm(prompt, model)
        return {"model": model, "draft": draft}

    async def generate_drafts_async(self, user_instructions, story_data):
        """Generate multiple drafts asynchronously"""

        # Run draft generation concurrently
        loop = asyncio.get_event_loop()
        tasks = []
        for model in config.MODELS["drafts"]:
            task = loop.run_in_executor(None, self.generate_draft, user_instructions, story_data, model)
            tasks.append(task)

        drafts = await asyncio.gather(*tasks)
        return drafts

    def generate_draft_comparison(self, user_instructions, story_data):
        """Generate a detailed comparison analysis of all drafts"""
        drafts_text = "\n\n---\n\n".join([
            f"DRAFT FROM {draft['model']}:\n{draft['draft']}" 
            for draft in story_data['drafts']
        ])

        prompt = f"""
        ANALYZE AND COMPARE multiple story drafts to identify their strengths and weaknesses.
        
        ORIGINAL USER INSTRUCTIONS: {user_instructions}
        STORY PLAN: {story_data['story_plan']}
        CHARACTERS: {story_data['characters']}
        
        DRAFTS TO COMPARE:
        {drafts_text}
        
        Please provide a detailed comparative analysis covering:
        
        1. **ADHERENCE TO VISION**: How well does each draft follow the original user instructions?
        2. **CHARACTER DEVELOPMENT**: Which drafts have the most compelling character arcs?
        3. **PLOT STRUCTURE**: How well does each draft follow the story plan? Any notable deviations?
        4. **WRITING QUALITY**: Assess prose style, dialogue, descriptive language in each draft.
        5. **EMOTIONAL IMPACT**: Which drafts are most engaging and emotionally resonant?
        6. **STRENGTHS OF EACH DRAFT**: Specific elements worth preserving from each version.
        7. **WEAKNESSES OF EACH DRAFT**: Areas where each draft falls short.
        8. **SPECIFIC RECOMMENDATIONS**: Concrete suggestions for the final synthesis.
        
        Focus on identifying the BEST elements from EACH draft that should be combined in the final version.
        
        Comparative Analysis:
        """
        model = self.get_model_for_stage("comparison")
        return self.call_llm(prompt, model)

    def generate_final_story(self, user_instructions, story_data, comparison_analysis):
        """Generate the final story using the comparison analysis for enhanced context"""
        drafts_text = "\n\n".join([f"Draft from {draft['model']}:\n{draft['draft']}" 
                                 for draft in story_data['drafts']])

        prompt = f"""
        SYNTHESIZE A FINAL STORY by combining the best elements from multiple drafts, guided by expert analysis.
        
        ORIGINAL USER INSTRUCTIONS: {user_instructions}
        STORY PLAN: {story_data['story_plan']}
        CHARACTERS: {story_data['characters']}
        
        EXPERT COMPARATIVE ANALYSIS OF DRAFTS:
        {comparison_analysis}
        
        AVAILABLE DRAFTS:
        {drafts_text}
        
        Using the detailed comparative analysis above, create a final version that:
        
        1. **PRIORITIZE BEST ELEMENTS**: Use the analysis to identify and incorporate the strongest elements from each draft
        2. **FOLLOW USER VISION**: Faithfully adhere to the original user instructions
        3. **MAINTAIN CONSISTENCY**: Ensure character consistency and plot coherence
        4. **ENHANCE QUALITY**: Improve upon the weaknesses identified in the analysis
        5. **BALANCE STYLES**: Blend the best writing styles and techniques from different drafts
        6. **STRONG OPENING**: Use the most engaging opening from any draft
        7. **SATISFYING ENDING**: Use the most resonant conclusion from any draft
        8. **WORD COUNT**: Aim for 600-900 words
        
        Pay special attention to the specific recommendations in the comparative analysis.
        
        Final Story:
        """
        model = self.get_model_for_stage("final")
        return self.call_llm(prompt, model)

    def parse_characters(self, characters_text):
        """Parse character information from LLM response"""
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
            user_instructions = self.instructions_text.get(1.0, tk.END).strip()
            self.generator.story_data["user_instructions"] = user_instructions

            self.update_status("Generating high-level description...")
            high_level_desc = self.generator.generate_high_level_description(user_instructions)
            self.generator.story_data["high_level_description"] = high_level_desc
            self.append_output("=== HIGH LEVEL DESCRIPTION ===\n" + high_level_desc)

            self.update_status("Generating characters...")
            characters_text = self.generator.generate_characters(user_instructions, high_level_desc)
            characters = self.generator.parse_characters(characters_text)
            self.generator.story_data["characters"] = characters
            self.append_output("=== CHARACTERS ===\n" + characters_text)

            self.update_status("Generating story plan...")
            story_plan = self.generator.generate_story_plan(user_instructions, high_level_desc, characters)
            self.generator.story_data["story_plan"] = story_plan
            self.append_output("=== STORY PLAN ===\n" + story_plan)

            self.update_status("Generating drafts (this may take a while)...")
            # Run async drafts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            drafts = loop.run_until_complete(
                self.generator.generate_drafts_async(user_instructions, self.generator.story_data)
            )
            self.generator.story_data["drafts"] = drafts

            for i, draft in enumerate(drafts, 1):
                self.append_output(f"=== DRAFT {i} ({draft['model']}) ===\n" + draft['draft'])

            # Generate comparison analysis
            self.update_status("Analyzing and comparing drafts...")
            comparison_analysis = self.generator.generate_draft_comparison(user_instructions, self.generator.story_data)
            self.generator.story_data["draft_comparison"] = comparison_analysis
            self.append_output("=== DRAFT COMPARISON ANALYSIS ===\n" + comparison_analysis)

            self.update_status("Generating final story (with enhanced context)...")
            final_story = self.generator.generate_final_story(user_instructions, self.generator.story_data, comparison_analysis)
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
    # Check if API key is set
    if config.USE_GEMINI:
        if config.GEMINI_API_KEY == "your-gemini-api-key-here":
            print("ERROR: Please set your Gemini API key in config.py")
            return
    else:
        if config.OPENROUTER_API_KEY == "your-api-key-here":
            print("ERROR: Please set your OpenRouter API key in config.py")
            return

    root = tk.Tk()
    app = StoryGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()