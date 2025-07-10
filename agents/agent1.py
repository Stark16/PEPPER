
import os
import json
import uuid
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class JobScreener:
    def __init__(self, model_to_load="microsoft/Phi-3.5-mini-instruct", device_map="auto"):
        self.load_LLM(model_to_load, device_map)
        self.generation_args = {
            "max_new_tokens": 512,
            "temperature": 0.1,
            "do_sample": True
        }

    def load_LLM(self, model_to_load, device_map):
        self.tokenizer = AutoTokenizer.from_pretrained(model_to_load, trust_remote_code=False, padding_side='left')
        self.model = AutoModelForCausalLM.from_pretrained(model_to_load, device_map=device_map, torch_dtype="auto", trust_remote_code=False)

    def build_prompt(self, job):
        return f"""
                You are a helpful assistant trained to determine the legitimacy of job postings. Given the following job listing, analyze and return a JSON object with the following fields:
                - "label": "Real" or "Fake"
                - "score": Integer from 0 to 10
                - "reason": Short explanation
                - "flags": List of any suspicious elements
                - "application_type": "Easy Apply" or "External"

                Example Output:
                {{
                "label": "Fake",
                "score": 3,
                "reason": "Job description is vague and company is unknown.",
                "flags": ["unclear company", "low word count", "buzzword soup"],
                "application_type": "Easy Apply"
                }}

                Job Posting:
                Title: {job['title']}
                Company: {job['company']}
                Link: {job['link']}
                Source: {job['scraped_from']}
                Description: {job['description']}
                """

    def detect_easy_apply(self, job):
        link = job.get('link', '').lower()
        if "linkedin.com/jobs" in link and "apply" in job.get('description', '').lower():
            return "Easy Apply"
        return "External"

    def query_llm(self, prompt):
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes job postings."},
            {"role": "user", "content": prompt}
        ]
        tokenized_chat = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to("cuda")
        output = self.model.generate(tokenized_chat, **self.generation_args)
        decoded = self.tokenizer.batch_decode(output, skip_special_tokens=False, clean_up_tokenization_spaces=True)
        response = decoded[0].split("<|assistant|>")[-1].split("<|end|>")[0]
        return response

    def analyze_job(self, job_dict):
        prompt = self.build_prompt(job_dict)
        raw_response = self.query_llm(prompt)

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            result = {
                "label": "Unknown",
                "score": 0,
                "reason": "Failed to parse LLM response",
                "flags": ["parse_error"],
                "application_type": self.detect_easy_apply(job_dict)
            }
        return result

    def run(self, job):
        return self.analyze_job(job)
