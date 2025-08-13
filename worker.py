import os
import time
import json
from data.dbms_manager import DBManager
from utils.wordparser import WordFileManager
from utils.model_llm import ModelLLM
from agents import agent2, agent3, agent4, agent5

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
            print(f"\t\t [📦-INFO] Updating DataBase ...")
            self.OBJ_db.update_task_info(task["Id"], agent_outputs, "pending")


        if task['Status'] == 'approved':

            agent5_instance = agent5.Agent5ResumeCoach(self.OBJ_ModelLLM)
            agent_outputs = self.OBJ_db.fetch_request_state(task["Id"])

            print(f"\t\t [📦-INFO] Fetching Resume JSON ...")
            PATH_in_full = os.path.join(self.PATH_self_dir ,'data', resume_details['FilePath'])
            OBJ_WordFile = WordFileManager(PATH_in_full)
            OBJ_WordFile.read()
            resume_json = OBJ_WordFile.export_json()

            print(f"\t\t [🧠-INFO] Running Agent5 ...")
            resume_changes = agent5_instance.run(agent_outputs["agents"]["Agent4"], resume_json)
            OBJ_WordFile.mark_updates_for_docxedit(resume_changes)

            output_file_name = resume_details['Id'] + '.docx'
            PATH_out_rel = resume_details['FilePath'].replace('default_resumes', 'curated_resumes')
            PATH_out_rel = PATH_out_rel.replace(os.path.basename(resume_details['FilePath']), output_file_name)

            print(f"\t\t [📦-INFO] Writing Curated Resume ...")
            PATH_out_full = os.path.join(self.PATH_self_dir, 'data', PATH_out_rel)
            OBJ_WordFile.write(PATH_out_full)

            updated_agent_outputs = {"Agent2" : agent_outputs["agents"]["Agent2"],
                                     "Agent3" : agent_outputs["agents"]["Agent3"],
                                     "Agent4" : agent_outputs["agents"]["Agent4"],
                                     "Agent5" : resume_json}
            
            # Create Agent2 Output for Curated Resume-
            OBJResumeCurated = WordFileManager(PATH_out_full)
            OBJResumeCurated.read()
            parsed_resume_curated = OBJResumeCurated.export_json()

            print(f"\t\t [🧠-INFO] Running Agent2 ...")
            agent2_instance = agent2.Agent2VirtualMe(self.OBJ_ModelLLM)
            vimi_json = agent2_instance.run(parsed_resume_curated)

            print(f"\t\t [📦-INFO] Updating DataBase ...")
            self.OBJ_db.update_tblResume(task["ResumeId"], vimi_json, FilePath=PATH_out_rel)
            self.OBJ_db.update_task_info(task["Id"], updated_agent_outputs, "finished")
            

    def replace_paragraph_text(doc, old_string, new_string, include_tables=True, show_errors=False):
        """
        Replaces the entire paragraph text if it matches old_string exactly.
        Preserves paragraph formatting and works for both body and tables.
        """
        string_instances_replaced = 0

        # Replace in document body
        for paragraph in doc.paragraphs:
            if paragraph.text.strip() == old_string.strip():
                # Replace all runs with a single run containing new_string
                for run in paragraph.runs:
                    run.text = ""
                paragraph.add_run(new_string)
                string_instances_replaced += 1
                print(f'[✅] Replaced paragraph: "{old_string}" -> "{new_string}"')
            else:
                if show_errors and old_string in paragraph.text:
                    print(f'[!] Partial match found but not replaced: "{paragraph.text}"')

        # Replace in tables if requested
        if include_tables:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip() == old_string.strip():
                                for run in paragraph.runs:
                                    run.text = ""
                                paragraph.add_run(new_string)
                                string_instances_replaced += 1
                                print(f'[✅] Replaced table paragraph: "{old_string}" -> "{new_string}"')
                            else:
                                if show_errors and old_string in paragraph.text:
                                    print(f'[!] Partial match found in table but not replaced: "{paragraph.text}"')

        print(f'Summary: Replaced {string_instances_replaced} instances of "{old_string}" with "{new_string}"')
                        

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