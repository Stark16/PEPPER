import os
import json
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.wordparser import WordFileManager
from utils.model_llm import ModelLLM

class Agent5ResumeCoach:
    
    def __init__(self, OBJ_model:ModelLLM):

        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_prompt = (
                                "You are Agent 5 — a resume editing agent.\n\n"
                                "Your job is to generate precise replacements or deletions for only the sections that require changes in the candidate's resume.\n\n"
                                "You will receive:\n"
                                "- The original resume in JSON format. The JSON contains structured sections like SUMMARY, EXPERIENCE, EDUCATION, SKILLS, etc.\n"
                                "- Editing instructions from a resume coach agent named Agent 4 (strategic suggestions for improving specific sections).\n\n"
                                "Your task is to rewrite or delete only the content that needs to be changed, section by section.\n\n"
                                "**Output format:**\n"
                                "Return a JSON list. Each item in the list must have:\n"
                                '- "section": the section being changed (e.g., "SUMMARY", "EXPERIENCE")\n\n'
                                "Then one of the following actions:\n"
                                "- If modifying content:  \n"
                                '  "replace": an object with:\n'
                                "    - \"original\": the exact block of text to be replaced (verbatim from the resume)\n"
                                "    - \"updated\": the improved replacement text with identical formatting and structure\n\n"
                                "- If deleting content:  \n"
                                '  "delete": the exact block of text that should be removed (verbatim)\n\n'
                                "Preserve formatting such as indentation, bullet points, and line breaks. Do not rewrite unchanged sections. "
                                "Do not output any explanations — only the JSON list of modifications.\n\n"
                                "Output nothing else.")
        
        self.OBJ_ModelLLM = OBJ_model
        self.generation_args = {
            "max_new_tokens": 768,
            "temperature": 0.2,
            "do_sample": True}

    def build_prompt(self, resume_json, coach_feedback):

        if not isinstance(resume_json, str):
            resume_json = json.dumps(resume_json, ensure_ascii=False, indent=2)
        if not isinstance(coach_feedback, str):
            coach_feedback = json.dumps(coach_feedback, ensure_ascii=False, indent=2)

        prompt = (
            "Use the following data to generate your edit list.\n\n"
            f"Resume JSON:\n{resume_json}\n\n"
            f"Resume Coach Suggestions:\n{coach_feedback}\n\n"
        )
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}]

        return messages


        
    def parse_response(self, response):

        # Remove code block markers and language hints (e.g., ```json ... ```)
        if response.strip().startswith("```"):
            # Remove all triple backticks and possible language hints
            response = re.sub(r"^```[a-zA-Z]*\n?", "", response.strip())
            response = re.sub(r"\n?```$", "", response.strip())

        # Try to extract the first valid JSON array or object
        try:
            # Try to find the first JSON array in the string
            match = re.search(r'(\[.*\])', response, re.DOTALL)
            if match:
                response_json_str = match.group(1)
                response_result = json.loads(response_json_str)
                return response_result
            # Fallback: try to find the first JSON object
            match = re.search(r'(\{.*\})', response, re.DOTALL)
            if match:
                response_json_str = match.group(1)
                response_result = json.loads(response_json_str)
                return response_result
            # Last resort: try to load the whole string
            response_result = json.loads(response)
            return response_result
        except Exception:
            return {"error": "Could not parse agent5 output", "raw": response}
        

    def run(self, resume_coach_feedback, resume_json):

        agent5_inputs = self.build_prompt(resume_coach_feedback, resume_json)
        # Batch tokenize
        agent5_response = self.OBJ_ModelLLM.query(agent5_inputs, self.generation_args)

        # Parse recruiter output (still expects JSON)
        agent5_result = self.parse_response(agent5_response)
        # print(agent5_response)
        # Parse ATS output (expects a flat, comma-separated list)

        return {"resume_changes": agent5_result}

    def write_json(self, json_obj):
        os.makedirs(os.path.join(self.PATH_self_dir, '../data'), exist_ok=True)
        out_path = os.path.join(self.PATH_self_dir, '../data/agent5_gemini.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Accept JSON input as a string (for example, from a file or direct input)

    agent4_json_path = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\agent4_gemini.json"

    # Load resume JSON as before
    resume_path = r"data/candidate_data/default_resumes/f4217103-e728-487c-aa93-8dcba245ef83.docx"
    OBJ = WordFileManager(resume_path)
    OBJ_ModelLLM = ModelLLM()
    OBJ.read()
    resume_json = OBJ.export_json()  # returns dict

    # Load agent2 and agent3 outputs
    with open(agent4_json_path, 'r', encoding='utf-8') as f:
        resume_coach_feedback = json.load(f)

    OBJ_ModelLLM = ModelLLM()
    agent = Agent5ResumeCoach(OBJ_ModelLLM)
    result = agent.run(resume_coach_feedback, resume_json)
    print(json.dumps(result, indent=2))
    agent.write_json(result)