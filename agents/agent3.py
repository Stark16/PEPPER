import os
import json

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.model_llm import ModelLLM

class Agent3Recruiter:
    
    def __init__(self, OBJ_model:ModelLLM):

        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_prompt = (
            "You are a highly experienced hiring manager reviewing a job description to define the ideal candidate profile. "
            "Your task is to critically and practically extract the following two categories:\n\n"
            "1. Must-Have: These are non-negotiable skills, qualifications, or experiences that are essential for the role.\n"
            "2. Good-to-Have: These are desirable extras that give a candidate an edge, but are not strictly required.\n\n"
            "Avoid listing vague soft skills unless the job specifically emphasizes them. Be honest, concise, and realistic about what matters most for this role.")
        
        self.ats_prompt = (
            "You are an advanced Applicant Tracking System (ATS) analyzing a job description. "
            "Extract only the most relevant **keywords, tools, technologies, certifications, and frameworks** that should be present in a resume. "
            "Ignore full sentences or soft skills. Output just a flat, comma-separated list of keywords.")
        
        self.OBJ_ModelLLM = OBJ_model
        self.generation_args = {
            "max_new_tokens": 768,
            "temperature": 0.2,
            "do_sample": True}

    def build_prompt(self, job_json, mode="recruiter"):
        company = job_json.get("company", None)
        title = job_json.get("title", None)
        description = job_json.get("description", "")
        company_str = f"Company: {company}\n" if company else ""
        title_str = f"Job Title: {title}\n" if title else ""
        if mode == "recruiter":
            prompt = (
                f"{company_str}{title_str}"
                f"Job Description:\n{description}\n\n"
                "Return a JSON object with two fields:\n"
                "- must_haves: list of qualities/skills/traits that are absolutely required\n"
                "- good_to_haves: list of qualities/skills/traits that are beneficial but not mandatory\n"
                "Be realistic and practical, not just idealistic.\n")
            
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}]
            return messages
        
        elif mode == "ats":
            prompt = (
                f"{company_str}{title_str}"
                f"Job Description:\n{description}\n\n"
                "Extract only the top 5-8 relevant keywords, tools, technologies, certifications, and frameworks that should be present in a resume. "
                "Do not include keywords like the company name, location, product name, or any other non-essential terms."
                "Ignore full sentences or soft skills. Output just a flat, comma-separated list of keywords.")
            
            messages = [{"role": "system", "content": self.ats_prompt}, {"role": "user", "content": prompt}]
            return messages
        
        else:
            raise ValueError("mode must be 'recruiter' or 'ats'")
        
    def parse_response(self, response, mode:str):
        if mode == "recruiter":
            try:
                recruiter_start = response.index('{')
                recruiter_end = response.rindex('}') + 1
                recruiter_json_str = response[recruiter_start:recruiter_end]
                recruiter_result = json.loads(recruiter_json_str)
            except Exception:
                recruiter_result = {"error": "Could not parse recruiter output", "raw": response}
            
            return recruiter_result
        
        elif mode == "ats":
            ats_keywords = []
            try:
                ats_text = response
                ats_text = ats_text.replace('[','').replace(']','').replace('"','').replace("'","")
                ats_keywords = [kw.strip() for kw in ats_text.split(',') if kw.strip()]
            except Exception:
                ats_keywords = ["Could not parse ATS output", response]

            return ats_keywords

    def run(self, job_json_str):
        # Accepts a JSON string as input
        if isinstance(job_json_str, str):
            job_json = json.loads(job_json_str)
        else:
            job_json = job_json_str  # Already a dict

        recruiter_messages = self.build_prompt(job_json, mode="recruiter")
        ats_messages = self.build_prompt(job_json, mode="ats")
        # Batch tokenize

        inputs = [recruiter_messages, ats_messages]
        recruiter_decoded, ats_decoded = self.OBJ_ModelLLM.query(inputs, self.generation_args)

        recruiter_response = recruiter_decoded.split("<|assistant|>")[-1].split("<|end|>")[0].strip()
        ats_response = ats_decoded.split("<|assistant|>")[-1].split("<|end|>")[0].strip()
        # Parse recruiter output (still expects JSON)
        recruiter_result = self.parse_response(recruiter_response, mode="recruiter")
        # Parse ATS output (expects a flat, comma-separated list)
        ats_keywords = self.parse_response(ats_response, mode="ats")

        return {"recruiter": recruiter_result, "ats": ats_keywords}

    def write_json(self, json_obj):
        os.makedirs(os.path.join(self.PATH_self_dir, '../data'), exist_ok=True)
        out_path = os.path.join(self.PATH_self_dir, '../data/agent3.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Accept JSON input as a string (for example, from a file or direct input)
    example_json = {
                    "title": "Deep Learning Manipulation Engineer, Optimus",
                    "jobid": "224501",
                    "post_date": "Not specified",
                    "company": "Tesla",
                    "link": "https://www.tesla.com/careers/search/job/deep-learning-manipulation-engineer-optimus-224501",
                    "scraped_from": "Tesla Careers",
                    "location": "Not specified",
                    "experience_required": "Not specified",
                    "company_size": "100000+",
                    "salary_range": "$140,000 - $420,000/annual salary",
                    "application_website": "Company Website",
                    "sponsorship": "Not Specified",
                    "referral": False,
                    "description": "Tesla is on a path to build humanoid robots at scale to automate repetitive and boring tasks. Core to the Optimus, the manipulation stack presents a unique opportunity to work on state-of-the-art algorithms for object manipulation culminating in their deployment to real world production applications. Our robotic manipulation software engineers develop and own this stack from inception to deployment. Most importantly, you will see your work repeatedly shipped to and utilized by thousands of Humanoid Robots in real world applications. What You’ll Do Design and develop our learned robotic manipulation software stack and algorithms Develop robotic manipulation capabilities including but not limited to (re)grasping, pick-and-place, and more dexterous behaviors to enable useful work in both structured and unstructured environments Model robotic manipulation processes to enable analysis, simulation, planning, and controls Reason about uncertainty due to measurements and physical interaction with the environment, and develop algorithms that adapt well to imperfect information Assist with overall software architecture design, including designing interfaces between subsystems Ship production quality, safety-critical software Collaborate with a team of exceptional individuals laser focused on bringing useful bi-ped humanoid robots into the real world What You’ll Bring Production quality modern C++ or Python Experience in deep imitation learning or reinforcement learning in realistic applications Exposure to robotics learning through tactile and/or vision-based sensors. Experience writing both production-level Python (including Numpy and Pytorch) and modern C++ Proven track record of training and deploying real world neural networks Familiarity with 3D computer vision and/or graphics pipelines Experience with Natural Language Processing Experience with distributed deep learning systems Prior work in Robotics, State estimation, Visual Odometry, SLAM, Structure from Motion, 3D Reconstruction"
                    }
    OBJ_ModelLLM = ModelLLM()
    agent = Agent3Recruiter(OBJ_ModelLLM)
    result = agent.run(example_json)
    print(json.dumps(result, indent=2))
    agent.write_json(result)