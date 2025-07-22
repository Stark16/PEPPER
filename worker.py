import os
import time
import json
from data.dbms_manager import DBManager
from utils.wordparser import WordFileManager
from utils.model_llm import ModelLLM
from agents import agent2, agent3, agent4

class Worker:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.initialize_utils()


    def initialize_utils(self):

        self.OBJ_db = DBManager()
        self.OBJ_db.test_connection()
        print("\t\t [✅-INFO] DBManager initialized successfully.")

        self.OBJ_ModelLLM = ModelLLM()
        print("\t\t [✅-INFO] ModelLLM initialized successfully.")

    def parse_resume(self, task):

        self.OBJ_db.update_task_info(task["Id"], status="processing")
        print(f"\t\t [📦-INFO] Parsing resume ...")
        
        resume_path = os.path.join(self.PATH_self_dir, 'data', task["Input"])
        OBJResume = WordFileManager(resume_path)
        OBJResume.read()
        parsed_resume = OBJResume.export_json()

        print(f"\t\t [🧠-INFO] Running Agent2 ...")
        agent2_instance = agent2.Agent2VirtualMe(self.OBJ_ModelLLM)
        vimi_json = agent2_instance.run(parsed_resume)

        print(f"\t\t [📦-INFO] Updating DataBase ...")
        # Prepare agent_outputs dict for update_task_info
        agent_outputs = {"Agent2": vimi_json}
        # You can set status as needed, e.g., 'parsed' or 'finished'
        status = "finished"
        self.OBJ_db.update_task_info(task["Id"], agent_outputs, status)
        self.OBJ_db.update_tblResume(task["ResumeId"], vimi_json)


    def curate_resume(self, task):

        resume_details = self.OBJ_db.fetch_resume_detail(task["ResumeId"], fetch_resume_parse=True)

        if task['Status'] == 'queued':
            agent_outputs = {"Agent2": json.loads(resume_details["ResumeJson"])}
            # print(json.dumps(agent_outputs["Agent2"], indent=2))    

            print(f"\t\t [🧠-INFO] Running Agent3 ...")
            agent3_instance = agent3.Agent3Recruiter(self.OBJ_ModelLLM)
            agent3_recruiter_response = agent3_instance.run(task["Input"])
            agent_outputs.update({"Agent3": agent3_recruiter_response})
            # print(json.dumps(agent_outputs["Agent3"], indent=2))

            print('\t\t [🧠-INFO] Running Agent4 ...')
            agent4_instance = agent4.Agent4CareerAdvisor(self.OBJ_ModelLLM)
            agent4_career_coach_response = agent4_instance.run(agent_outputs["Agent2"],
                                                               agent_outputs["Agent3"],
                                                               resume_details['parsed_json'])
            agent_outputs.update({"Agent4": agent4_career_coach_response})
            # print(json.dumps(agent_outputs["Agent4"], indent=2))
            self.OBJ_db.update_task_info(task["Id"], agent_outputs, "pending")


    def start_worker_loop(self):
        print("\n\n\t\t[🚀-INIT] Process Queue Worker Intiated.")
        
        while True:
            task = self.OBJ_db.get_next_pending_request()  # your own logic

            if task:
                print_task_header = f"\n\n\t\t [📦-INFO] " + "="*10 + f" Running task - [{task['Id']}] | Type - [{task["Type"]}] " + "="*10
                print(print_task_header)
                
                if task["Type"] == "Parse":
                    self.parse_resume(task)
                elif task["Type"] == "Curate":
                    self.curate_resume(task)
                
                print("\t\t"+"="*(len(print_task_header)//2) + " [✅-INFO] Task completed! " + "="*(len(print_task_header)//2) + "\n\n")


            time.sleep(10)

if __name__ == "__main__":
    # Start the worker loop
    worker = Worker()
    worker.start_worker_loop()