import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
import torch

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.wordparser import WordFileManager

class Agent2VirtualMe:
    def __init__(self, model_to_load="microsoft/Phi-3.5-mini-instruct", device_map="auto"):

        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_prompt = (
            "You are Agent 2 — a highly analytical hiring manager reviewing a resume with limited time. "
            "You are given a structured JSON representation of a candidate’s resume. Your job is to perform a fast but insightful read of the resume, mimicking how a real recruiter or hiring manager might form impressions within 5–10 seconds of reading.\n\n"
            
            "Extract and return the following:\n"
            
            "1. title_impression: A one-line title that summarizes this candidate professionally (e.g., 'AI Researcher', 'Applied Scientist', 'ML Generalist with Start-up Experience')\n"
            "2. strengths: A list of bullet points summarizing clear technical and domain strengths (tools, frameworks, areas of depth, problem-solving approach, etc.)\n"
            "3. resume_style: A one-liner about the *type* of resume this is, based on the section ordering and emphasis (e.g., 'Academia-leaning research resume', 'Industry-ready engineering profile')\n"
            "4. section_analysis: A brief interpretation of what each major section tells you about the candidate. For example, the SUMMARY might indicate confidence, the EXPERIENCE might show initiative, and the SKILLS might reflect specialization vs. generalism.\n"
            
            "Behave like someone forming quick impressions but with depth and judgment. Do not repeat raw resume content. Your tone should be smart, neutral, and professional.\n\n"
            
            "Output your response strictly in the following JSON format:\n\n"
            "{\n"
            "  \"title_impression\": \"<string>\",\n"
            "  \"strengths\": [\"<string>\", \"<string>\", ...],\n"
            "  \"resume_style\": \"<string>\",\n"
            "  \"section_analysis\": {\n"
            "    \"SUMMARY\": \"<string>\",\n"
            "    \"EXPERIENCE\": \"<string>\",\n"
            "    \"EDUCATION\": \"<string>\",\n"
            "    \"PROJECTS\": \"<string>\",\n"
            "    \"SKILLS\": \"<string>\"\n"
            "  }\n"
            "}\n\n"
            
            "If a section is missing from the input, skip it in your output."
        )
        self.load_LLM(model_to_load, device_map)
        self.generation_args = {
            "max_new_tokens": 768,
            "temperature": 0.2,
            "do_sample": True
        }

    def load_LLM(self, model_to_load, device_map):
        self.tokenizer = AutoTokenizer.from_pretrained(model_to_load, trust_remote_code=False, padding_side='left')
        self.model = AutoModelForCausalLM.from_pretrained(model_to_load, device_map=device_map, torch_dtype="auto", trust_remote_code=False)

    def build_prompt(self, resume_json: dict):
        resume_str = json.dumps(resume_json, indent=2)
        prompt = (
            f"Resume JSON:\n{resume_str}\n\n"
            "Return a single narrative summary of the candidate's strengths, technical areas, and unique professional themes."
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return messages

    def parse_response(self, response:str):
        try:
            recruiter_start = response.index('{')
            recruiter_end = response.rindex('}') + 1
            recruiter_json_str = response[recruiter_start:recruiter_end]
            recruiter_result = json.loads(recruiter_json_str)
        except Exception:
            recruiter_result = {"error": "Could not parse recruiter output", "raw": response}
        
        return recruiter_result
    

    def run(self, resume_json: dict):
        prompt = self.build_prompt(resume_json)
        inputs = self.tokenizer.apply_chat_template(prompt, add_generation_prompt=True, return_tensors="pt", padding=True).to(self.model.device)

        t1 = time.time()
        with torch.no_grad():
            output = self.model.generate(inputs, **self.generation_args)
        print("Total Generation Time:", time.time() - t1)
        response = self.tokenizer.batch_decode(output, skip_special_tokens=False, clean_up_tokenization_spaces=True)
        response = response[0].split("<|assistant|>")[-1].split("<|end|>")[0].strip()
        response = self.parse_response(response)
        return response
    
    def write_json(self, json_obj):
        os.makedirs(os.path.join(self.PATH_self_dir, '../data'), exist_ok=True)
        out_path = os.path.join(self.PATH_self_dir, '../data/agent2.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Example usage: parse a resume and generate a synopsis
    resume_path = r"d:\Career\Resume\Pradyumn_Pathak_Resume.docx"
    OBJ = WordFileManager(resume_path)
    OBJ.read()
    resume_json = OBJ.export_json()  # returns dict
    agent = Agent2VirtualMe()
    synopsis = agent.run(resume_json)
    print("\n--- Resume Synopsis ---\n")
    print(json.dumps(synopsis, indent=2))
    agent.write_json(synopsis)