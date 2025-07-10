import os
import json
import uuid
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class Agent3Recruiter:
    def __init__(self, model_to_load="microsoft/Phi-3.5-mini-instruct", device_map="auto"):
        self.system_prompt = (
            "You are a super critical hiring manager. "
            "You must analyze job descriptions with a critical, practical, and realistic mindset. "
            "Your job is to extract must-have, good-to-have, and not-to-have qualities for the ideal candidate. "
            "Be honest, tough, but also practical about what is actually needed."
        )
        self.load_LLM(model_to_load, device_map)
        self.generation_args = {
            "max_new_tokens": 512,
            "temperature": 0.2,
            "do_sample": True
        }

    def load_LLM(self, model_to_load, device_map):
        self.tokenizer = AutoTokenizer.from_pretrained(model_to_load, trust_remote_code=False, padding_side='left')
        self.model = AutoModelForCausalLM.from_pretrained(model_to_load, device_map=device_map, torch_dtype="auto", trust_remote_code=False)

    def build_prompt(self, job_description, company_name=None):
        company_str = f"Company: {company_name}\n" if company_name else ""
        return f"""
{self.system_prompt}\n\n{company_str}Job Description:\n{job_description}\n\nReturn a JSON object with three fields:\n- must_haves: list of qualities/skills/traits that are absolutely required\n- good_to_haves: list of qualities/skills/traits that are beneficial but not mandatory\n- not_to_haves: list of qualities/skills/traits that would be a red flag or undesirable\nBe realistic and practical, not just idealistic.\n"""

    def run(self, job_description, company_name=None):
        prompt = self.build_prompt(job_description, company_name)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            output = self.model.generate(**inputs, **self.generation_args)
        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        # Try to extract the JSON part
        try:
            json_start = response.index('{')
            json_str = response[json_start:]
            result = json.loads(json_str)
        except Exception:
            result = {"error": "Could not parse model output", "raw": response}
        return result
