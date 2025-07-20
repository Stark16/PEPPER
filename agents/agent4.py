import json
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.wordparser import WordFileManager
from utils.model_llm import ModelLLM

class Agent4CareerAdvisor:
    
    def __init__(self, OBJ_ModelLLM:ModelLLM):

        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_prompt = (
            "You are Agent 4, the Career Coach.\n\n"
            "You help tailor a candidate's resume for a specific job by analyzing:\n"
            "- A summary of what the resume currently conveys (Agent 2)\n"
            "- A job description analysis from recruiter and ATS perspectives (Agent 3)\n"
            "- The actual resume structure in JSON format\n\n"
            "Your task is to identify which parts of the resume need improvement or adjustment, and recommend **section-wise** edits to improve alignment with the job.\n\n"
            "For each section or entry, output:\n"
            "- Whether it needs editing\n"
            "- A short reason\n"
            "- Clear edit instructions (e.g., what to emphasize, add, remove, or reword)\n\n"
            "Format your response as a clean JSON object. Output only the JSON. Be direct and information-dense."
        )
        self.OBJ_ModelLLM = OBJ_ModelLLM
        self.generation_args = {
            "max_new_tokens": 768,
            "temperature": 0.2,
            "do_sample": True
        }


    def build_prompt(self, resume_json: dict, vimi_json: dict, recruiter_json: dict):
        resume_str = json.dumps(resume_json, indent=2)
        vimi_str = json.dumps(vimi_json, indent=2)
        recruiter_str = json.dumps(recruiter_json, indent=2)
        prompt = (
            f"Resume summary from Agent 2 (VirtualMe):\n{vimi_str}\n\n"
            f"Recruiter/ATS analysis from Agent 3 (Recruiter):\n{recruiter_str}\n\n"
            f"Resume JSON:\n{resume_str}\n\n"
            "Based on the above, provide section-wise JSON suggestions for what to add, update, or remove in the resume to better align with the job. For each section or entry, specify if it needs editing, a short reason, and clear edit instructions. Output only the JSON."
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return messages

    def parse_response(self, response: str):
        
        # Try to extract the largest JSON object using regex
        try:
            matches = re.findall(r'{[\s\S]*}', response)
            # Pick the largest match
            if matches:
                json_candidate = max(matches, key=len)
                return json.loads(json_candidate)
        except Exception:
            pass
        # Fallback: try to parse the whole response
        try:
            return json.loads(response)
        except Exception:
            return {"error": "Could not parse agent4 output", "raw": response}
    
    def run(self, vimi_json: dict, recruiter_json: dict, resume_json: dict):
        messages = self.build_prompt(resume_json, vimi_json, recruiter_json)

        self.OBJ_ModelLLM.query(messages, self.generation_args)

        response = self.parse_response(response)
        return response
    
    def write_json(self, json_obj):
        os.makedirs(os.path.join(self.PATH_self_dir, '../data'), exist_ok=True)
        out_path = os.path.join(self.PATH_self_dir, '../data/agent4.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Example usage: parse a resume and generate a synopsis
    agent2_json_path = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\agent2.json"
    agent3_json_path = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\agent3.json"

    # Load resume JSON as before
    resume_path = r"d:\Career\Resume\Pradyumn_Pathak_Resume.docx"
    OBJ = WordFileManager(resume_path)
    OBJ_ModelLLM = ModelLLM()
    OBJ.read()
    resume_json = OBJ.export_json()  # returns dict

    # Load agent2 and agent3 outputs
    with open(agent2_json_path, 'r', encoding='utf-8') as f:
        vimi_json = json.load(f)
    with open(agent3_json_path, 'r', encoding='utf-8') as f:
        recruiter_json = json.load(f)

    agent = Agent4CareerAdvisor(OBJ_ModelLLM)
    output = agent.run(vimi_json, recruiter_json, resume_json)
    print("\n--- Agent 4 Suggestions ---\n")
    print(json.dumps(output, indent=2))
    agent.write_json(output)