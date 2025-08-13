import os
import json
import pyodbc
from utils.candidate_resume_database import CandidateResumeDatabase
from utils.wordparser import WordFileManager
import uuid
import datetime


class DBManager:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.candidate_db = CandidateResumeDatabase()
        self.connection_string = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-SC072N0\MSSQLSERVER01;DATABASE=pepper;Trusted_Connection=yes;'

    def test_connection(self):
        """Test the database connection!"""

        try:
            self.conn = pyodbc.connect(self.connection_string)
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                print("\t\t [✅-INFO] Connection successful!")
                return True
            else:
                print("\t\t [⚠️-ERROR] Connected, but unexpected result:", result)
                return False

        except pyodbc.Error as e:
            print("\t\t [❌-ERROR] Connection failed:", e)
            return False
        finally:
            if 'conn' in locals():
                self.conn.close()

    def fetch_all_user_names(self):
        """
        Returns a list of all user names from tblUsers.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT Name FROM tblUsers")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Error fetching user names: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def verify_user_pin(self, Name: str, Pin: str):
        """
        Verifies if the given Name and 4-digit Pin match a user in the database.
        Returns (True, Id) if credentials are valid, (False, None) otherwise.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT Id FROM tblUsers WHERE Name = ? AND Pin = ?", Name, Pin)
            result = cursor.fetchone()
            if result:
                return True, result[0]
            else:
                return False, None
        except Exception as e:
            print(f"Error verifying user pin: {e}")
            return False, None
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def fetch_all_resume_names(self, UserId:str):
        """
        Fetches all resume names for a given user from the database.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT FilePath FROM tblResume WHERE UserId = ?", UserId)
            rows = cursor.fetchall()

            return [os.path.basename(row) for row in rows]
        
        except Exception as e:
            print(f"Error fetching resumes: {e}")
            return []
        
        finally:
            cursor.close()
            conn.close()

    def create_new_request(self, UserId: str, ResumeId: str, Status: str, EndPoint: str, Type: str, Input, created_on=None):
        """
        Creates a new entry in tblRequests.
        [Id, UserId, ResumeId, Status, EndPoint, CreatedOn, Type, Input]
        Returns True if successful, False and error message otherwise.
        """
        import datetime
        try:
            RequestId = str(uuid.uuid4())
            if created_on is None:
                created_on = datetime.datetime.now()
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tblRequests (Id, UserId, ResumeId, Status, EndPoint, CreatedOn, Type, Input)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                RequestId, UserId, ResumeId, Status, EndPoint, created_on, Type, Input
            )
            conn.commit()
            print(f"Request {RequestId} created successfully for user {UserId}.")
            return True, RequestId
        except Exception as e:
            print(f"Error creating request: {e}")
            return False, str(e)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def save_new_resume(self, UserId: str, ResumeName: str, file_bytes: bytes, IsCurated: bool = False, ResumeJson: str = None, candidate_db=None, created_on=None):
        """
        Saves a new resume entry in the database, saves the file, and creates a new request for parsing.
        Stores only the relative file path from the data folder in the DB.
        Returns (True, ResumeId) on success, (False, error_message) on failure.
        """
        try:
            ResumeId = str(uuid.uuid4())
            # Save the file as ResumeId.docx using CandidateResumeDatabase
            if candidate_db is None:
                from utils.candidate_resume_database import CandidateResumeDatabase
                candidate_db = CandidateResumeDatabase()
            filename = ResumeId + ".docx"
            save_path = candidate_db.save_resume_file(file_bytes, filename)
            # Compute relative path from data folder
            data_base = os.path.abspath(os.path.join(self.PATH_self_dir, '..', 'data'))
            rel_file_path = os.path.relpath(save_path, data_base).replace('\\', '/')
            rel_file_path = rel_file_path[1:] if rel_file_path.startswith('/') else rel_file_path
            # Use provided created_on or generate new
            if created_on is None:
                import datetime
                created_on = datetime.datetime.now()
            # Save entry in tblResume (now with CreatedOn)
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tblResume (Id, UserId, ResumeName, FilePath, IsCurated, ResumeJson, CreatedOn) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ResumeId, UserId, ResumeName, rel_file_path, IsCurated, ResumeJson, created_on
            )
            conn.commit()
            print(f"Resume {save_path} saved successfully for user {UserId}.")
            # Create a new request for parsing this resume, pass created_on for consistency
            status, result = self.create_new_request(
                UserId=UserId,
                ResumeId=ResumeId,
                Status="queued",
                EndPoint="/parse_resume",
                Type="Parse",
                Input=rel_file_path,
                created_on=created_on
            )
            if not status:
                print(f"Error creating parse request: {result}")
                return False, f"Resume saved but request creation failed: {result}"
            return True, ResumeId
        except Exception as e:
            print(f"Error saving resume: {e}")
            return False, str(e)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def curate_new_resume(self, user_id: str, resume_id: str, job_desc: dict):
        """
        Creates a curated resume entry in tblResume and a new request for curation.
        """
        try:
            # 1. Get file info
            file_path, resume_name = self.get_resume_file_info(resume_id)
            if not file_path:
                return False, "Resume file not found."
            # 2. Build new ResumeName
            file_path = file_path.split(self.PATH_self_dir)[1]
            file_path = file_path.replace('\\', '/')
            file_path = file_path[1:] if file_path.startswith('/') else file_path
            company = job_desc.get("company")
            jobid = job_desc.get("jobid")
            created_on = datetime.datetime.now()
            date_str = created_on.strftime("%Y%m%d")
            # Remove .docx extension if present
            base_name = resume_name[:-5] if resume_name.lower().endswith('.docx') else resume_name
            if company and jobid:
                new_resume_name = f"{base_name}_{company}_{jobid}.docx"
            else:
                new_resume_name = f"{base_name}_{date_str}.docx"
            # 3. Create new Id
            new_resume_id = str(uuid.uuid4())
            # 4. Insert into tblResume
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tblResume (Id, UserId, ResumeName, FilePath, IsCurated, ResumeJson, CreatedOn, EditedBy) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                new_resume_id, user_id, new_resume_name, file_path, True, None, created_on, resume_id
            )
            conn.commit()
            # 5. Create new request for curation
            status, result = self.create_new_request(
                UserId=user_id,
                ResumeId=new_resume_id,
                Status="queued",
                EndPoint="/curate_resume",
                Type="Curate",
                Input=json.dumps(job_desc),
                created_on=created_on
            )
            if not status:
                return False, f"Curated resume saved but request creation failed: {result}"
            return True, new_resume_id
        except Exception as e:
            print(f"Error curating resume: {e}")
            return False, str(e)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_resume_file_info(self, ResumeId: str):
        """
        Returns (absolute_file_path, resume_name) for the given ResumeId, or (None, None) if not found.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT FilePath, ResumeName FROM tblResume WHERE Id = ?", ResumeId)
            row = cursor.fetchone()
            if not row:
                return None, None
            rel_file_path, resume_name = row.FilePath, row.ResumeName
            abs_file_path = self.get_resume_full_path(rel_file_path)
            return abs_file_path, resume_name
        except Exception as e:
            print(f"Error fetching resume file info: {e}")
            return None, None
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_curated_resume(self, request_id: str):
        """
        Given a request_id, fetches the ResumeId from tblRequests, then returns (absolute_file_path, resume_name) using get_resume_file_info.
        Returns (abs_file_path, resume_name) or (None, None) if not found.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT ResumeId FROM tblRequests WHERE Id = ?", request_id)
                row = cursor.fetchone()
                if not row or not row[0]:
                    return None, None
                resume_id = row[0]
                return self.get_resume_file_info(resume_id)
        except Exception as e:
            print(f"Error fetching curated resume file info: {e}")
            return None, None

    def update_resume_file(self, ResumeId: str, ResumeName: str, file_bytes: bytes, candidate_db=None):
        """
        Replaces the file for the given ResumeId and updates ResumeName in tblResume.
        Returns (True, ResumeId) on success, (False, error_message) on failure.
        """
        try:
            if candidate_db is None:
                from utils.candidate_resume_database import CandidateResumeDatabase
                candidate_db = CandidateResumeDatabase()
            # Get the relative file path from DB
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT FilePath FROM tblResume WHERE Id = ?", ResumeId)
            row = cursor.fetchone()
            if not row:
                return False, "ResumeId not found."
            rel_file_path = row.FilePath[2:]
            # Get full path
            full_path = self.get_resume_full_path(rel_file_path)
            # Overwrite the file
            with open(full_path, 'wb') as f:
                f.write(file_bytes)
            # Update ResumeName if provided
            cursor.execute("UPDATE tblResume SET ResumeName = ? WHERE Id = ?", ResumeName, ResumeId)
            conn.commit()
            return True, ResumeId
        except Exception as e:
            print(f"Error updating resume: {e}")
            return False, str(e)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def rename_resume(self, ResumeId: str, new_name: str):
        """
        Updates the ResumeName for the given ResumeId in tblResume.
        Returns True on success, False otherwise.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("UPDATE tblResume SET ResumeName = ? WHERE Id = ?", new_name, ResumeId)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error renaming resume: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_resume_full_path(self, rel_file_path: str) -> str:
        """
        Given a relative file path from the database, return the absolute path by joining with the data directory.
        """
        data_base = os.path.abspath(os.path.join(self.PATH_self_dir, '..', 'data'))
        return os.path.join(data_base, rel_file_path)

    def fetch_user_requests(self, user_id: str, page_num: int, n: int):
        """
        Fetches paginated request entries for a user from tblRequests, joined with tblResume for ResumeName if ResumeId is present.
        Each entry includes endpoint, status (queue position or 'Finished'), and resumeName (if present).
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            # Fetch all requests for the user, joined with ResumeName if ResumeId is present, ordered by CreatedOn DESC
            query = '''
                SELECT r.Id, r.UserId, r.ResumeId, r.Status, r.Endpoint, r.CreatedOn, res.ResumeName
                FROM tblRequests r
                LEFT JOIN tblResume res ON r.ResumeId = res.Id
                WHERE r.UserId = ? AND (r.IsDeleted IS NULL OR r.IsDeleted != 1)
                ORDER BY r.CreatedOn DESC
            '''
            cursor.execute(query, user_id)
            rows = cursor.fetchall()
            # Pre-fetch all requests for queue position calculation (pending/processing, any user)
            cursor.execute('''
                SELECT Id, CreatedOn, Status FROM tblRequests WHERE Status IN ('pending', 'processing')
            ''')
            all_pending = cursor.fetchall()
            # Build a list of (Id, CreatedOn) for queue calculation
            pending_dict = {row.Id: row.CreatedOn for row in all_pending}
            # Prepare paginated result
            start = (page_num - 1) * n
            end = start + n
            result = []
            for idx, row in enumerate(rows):
                # Calculate queue position if not finished
                queue_position = None
                status_field_reply = queue_position

                if row.Status == 'finished':
                    status_field_reply = 'Finished'
                elif row.Status == 'pending':
                    status_field_reply = 'Pending'
                elif row.Status == 'approved':
                    status_field_reply = 'Approved'
                elif row.Status == 'rejected':
                    status_field_reply = 'Rejected'
                elif queue_position is not None and row.Status != 'finished':
                    queue_position += 1 if queue_position is not None else None
                    status_field_reply = queue_position

                entry = {
                    'RequestId': row.Id,
                    'endpoint': row.Endpoint,
                    'status': status_field_reply,
                    'CreatedOn' : row.CreatedOn.strftime("%Y-%m-%d %H:%M:%S"),
                    'resumeName': row.ResumeName if row.ResumeName else None
                }
                result.append(entry)
            # Pagination
            paginated = result[start:end]
            return paginated
        except Exception as e:
            print(f"Error fetching user requests: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def update_request_approval(self, request_id: str, approve: bool, agent4_updated:str):
        """
        Updates the Status of tblRequests for the given request_id to 'Approved' or 'Rejected'.
        Uses self.conn for the update.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        try:
            new_status = "approved" if approve else "rejected"
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE tblRequests SET Status = ? WHERE Id = ?",
                    new_status, request_id
                )
                self.conn.commit()
                cursor.execute(
                    "UPDATE tblRequestOutputs SET Agent4 = ? WHERE RequestId = ?",
                    agent4_updated, request_id
                )
                self.conn.commit()
            return True, None
        except Exception as e:
            print(f"Error updating request approval: {e}")
            self.conn.rollback()
            return False, str(e)

    def fetch_request_state(self, request_id: str):
        """
        Given a request_id, fetches the status from tblRequests. If status is 'finished' or 'pending',
        fetches agent outputs from tblRequestOutputs. Returns dict: {"status": ..., "agents": {...}}
        """

        agent_keys = ["Agent2", "Agent3", "Agent4", "Agent5"]
        try:

            cursor = self.conn.cursor()
            # 1. Get status from tblRequests
            cursor.execute("SELECT Status FROM tblRequests WHERE Id = ?", request_id)
            row = cursor.fetchone()
            if not row:
                return {"error": "Request not found."}
            status = row.Status if hasattr(row, 'Status') else row[0]
            agents = {k: None for k in agent_keys}
            if status in ("finished", "approved", "pending"):
                # 2. Get agent outputs from tblRequestOutputs
                cursor.execute(f"SELECT {', '.join(agent_keys)} FROM tblRequestOutputs WHERE RequestId = ?", request_id)
                agent_row = cursor.fetchone()
                if agent_row:
                    for idx, k in enumerate(agent_keys):
                        val = agent_row[idx]
                        if isinstance(val, str):
                            try:
                                agents[k] = json.loads(val)
                            except Exception:
                                agents[k] = val
                        else:
                            agents[k] = val
            # If status is 'queued', just return empty agent content
            return {"status": status, "agents": agents}
        except Exception as e:
            print(f"\t\t [❌-ERROR] fetch_request_state failed: {e}")
            return {"error": str(e)}
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.conn.close()

    def fetch_user_resumes(self, UserId: str, is_curated: bool):
        """
        Fetches resumes for a user filtered by IsCurated, ordered by CreatedOn (latest first).
        Returns a list of dicts: {ResumeId, Name, HasJson}
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Id, ResumeName, ResumeJson, CreatedOn FROM tblResume WHERE UserId = ? AND IsCurated = ? AND  (IsDeleted IS NULL OR IsDeleted != 1) ORDER BY CreatedOn DESC",
                UserId, is_curated
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                resume_id = row.Id
                name = row.ResumeName
                has_json = bool(row.ResumeJson and str(row.ResumeJson).strip())
                result.append({
                    "ResumeId": resume_id,
                    "Name": name,
                    "HasJson": has_json,
                    "ResumeJson" : row.ResumeJson,
                    "CreatedOn" : row.CreatedOn.strftime("%Y%m%d")
                })
            return result
        except Exception as e:
            print(f"Error fetching user resumes: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_next_pending_request(self):
        """
        Fetch the next pending request from tblRequest where Status != 'finished'.
        Prioritize Status='Approved', then order by CreatedOn (oldest first).
        Returns a dict with all columns for the top 1 entry, or None if no such entry exists.
        """
        query = (
            "SELECT TOP 1 [Id], [UserId], [ResumeId], [Status], [Endpoint], [CreatedOn], [Type], [Input] "
            "FROM tblRequests "
            # "WHERE [Status] IN ('queued', 'pending') "
            "WHERE [Status] IN ('queued', 'approved') "
            "ORDER BY CASE WHEN [Status]='Approved' THEN 0 ELSE 1 END, [CreatedOn] ASC"
        )
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    return dict(zip(columns, row))
                else:
                    return None
        except Exception as e:
            print(f"\t\t[❌-ERROR] get_next_pending_request failed: {e}")
            return None
        
    def update_task_info(self, request_id, agent_outputs: dict = None, status: str = "processing"):
        """
        If agent_outputs is None or empty, update tblRequests.Status to status and insert only RequestId/Status in tblResumeOutputs.
        Otherwise, insert agent outputs into tblResumeOutputs and update Status in tblResume.
        """
        try:
            if not agent_outputs:
                # Only update tblRequests and upsert minimal tblRequestOutputs
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE tblRequests SET Status = ? WHERE Id = ?", (status, request_id))
                    # Check if entry exists
                    cursor.execute("SELECT 1 FROM tblRequestOutputs WHERE RequestId = ?", (request_id,))
                    exists = cursor.fetchone()
                    if exists:
                        cursor.execute("UPDATE tblRequestOutputs SET Status = ? WHERE RequestId = ?", (status, request_id))
                    else:
                        cursor.execute("INSERT INTO tblRequestOutputs ([RequestId], [Status]) VALUES (?, ?)", (request_id, status))
                self.conn.commit()
            else:
                # Prepare columns and values for upsert
                agent_columns = ["Agent2", "Agent3", "Agent4", "Agent5"]
                set_clauses = []
                set_values = []
                for agent in agent_columns:
                    if agent in agent_outputs:
                        set_clauses.append(f"[{agent}] = ?")
                        set_values.append(json.dumps(agent_outputs[agent]))
                set_clauses.append("[Status] = ?")
                set_values.append(status)
                # Check if entry exists
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM tblRequestOutputs WHERE RequestId = ?", (request_id,))
                    exists = cursor.fetchone()
                    if exists:
                        # Update only the agent columns and status
                        update_stmt = f"UPDATE tblRequestOutputs SET {', '.join(set_clauses)} WHERE RequestId = ?"
                        cursor.execute(update_stmt, (*set_values, request_id))
                    else:
                        # Insert new row with only the provided agent columns and status
                        columns = ["RequestId"] + [agent for agent in agent_columns if agent in agent_outputs] + ["Status"]
                        values = [request_id] + [json.dumps(agent_outputs[agent]) for agent in agent_columns if agent in agent_outputs] + [status]
                        col_str = ", ".join(f"[{col}]" for col in columns)
                        param_str = ", ".join(["?"] * len(values))
                        insert_query = f"INSERT INTO tblRequestOutputs ({col_str}) VALUES ({param_str})"
                        cursor.execute(insert_query, values)
                    # Also update tblRequests.Status
                    cursor.execute("UPDATE tblRequests SET Status = ? WHERE Id = ?", (status, request_id))
                self.conn.commit()
        except Exception as e:
            print(f"\t\t [❌-ERROR] update_task_info failed: {e}")
            self.conn.rollback()

    def update_tblResume(self, resume_id: str, resume_json: str, FilePath: str = None):
        """
        Updates ResumeJson column in tblResume for the given resume_id. If FilePath is provided, also updates FilePath column.
        Uses self.conn for the update.
        """
        try:
            # Ensure resume_json is a string
            if not isinstance(resume_json, str):
                resume_json = json.dumps(resume_json, ensure_ascii=False)
            with self.conn.cursor() as cursor:
                if FilePath is not None:
                    FilePath = FilePath.replace('\\', '/')
                    FilePath = FilePath[1:] if FilePath.startswith('/') else FilePath
                    cursor.execute(
                        "UPDATE tblResume SET ResumeJson = ?, FilePath = ? WHERE Id = ?",
                        resume_json, FilePath, resume_id
                    )
                else:
                    cursor.execute(
                        "UPDATE tblResume SET ResumeJson = ? WHERE Id = ?",
                        resume_json, resume_id
                    )
                self.conn.commit()
            return True
        except Exception as e:
            print(f"\t\t [❌-ERROR] update_tblResume failed: {e}")
            self.conn.rollback()
            return False
        
    def fetch_resume_detail(self, resume_id: str, fetch_resume_parse: bool = False):
        """
        Fetches the full resume detail including Id, UserId, ResumeName, FilePath, IsCurated, ResumeJson, CreatedOn.
        If fetch_resume_parse is True, also returns parsed resume JSON using WordFileManager.export_json.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM tblResume WHERE Id = ?", resume_id)
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    result = dict(zip(columns, row))
                    if fetch_resume_parse:
                        rel_path = result.get("FilePath")
                        if rel_path:
                            abs_path = os.path.join(self.PATH_self_dir, rel_path)
                            try:
                                parser = WordFileManager(abs_path)
                                parser.read()
                                result["parsed_json"] = parser.export_json()
                            except Exception as e:
                                print(f"\t\t [❌-ERROR] Could not parse resume file: {e}")
                                result["parsed_json"] = None
                        else:
                            result["parsed_json"] = None
                    cursor.execute("SELECT ResumeJson FROM tblResume WHERE Id = ?", result['EditedBy'])
                    row = cursor.fetchone()
                    if row:
                        result["ResumeJson"] = row[0]
                    return result
                else:
                    return None
        except Exception as e:
            print(f"\t\t [❌-ERROR] fetch_resume_detail failed: {e}")
            return None

    def delete_db_entry(self, TableName: str, Id: str):
        """
        Soft delete an entry in tblResume or tblRequests. For tblResume, also deletes the associated file.
        Args:
            TableName (str): 'tblResume' or 'tblRequests'
            Id (str): UUID of the entry to delete
        Returns:
            (True, None) on success, (False, error_message) on failure
        """
        try:
            if TableName == "tblResume":
                # Set IsDeleted = 1 for the Id
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE tblResume SET IsDeleted = 1 WHERE Id = ?", Id)
                    # Fetch FilePath
                    cursor.execute("SELECT FilePath FROM tblResume WHERE Id = ?", Id)
                    row = cursor.fetchone()
                    if row and row[0]:
                        rel_file_path = row[0]
                        abs_file_path = self.get_resume_full_path(rel_file_path)
                        print(abs_file_path)
                        # Delete the file if it exists
                        if os.path.exists(abs_file_path):
                            os.remove(abs_file_path)
                self.conn.commit()
                return True, None
            elif TableName == "tblRequests":
                # Set IsDelete = 1 for the Id
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE tblRequests SET IsDeleted = 1 WHERE Id = ?", Id)
                self.conn.commit()
                return True, None
            else:
                return False, f"Unsupported TableName: {TableName}"
        except Exception as e:
            print(f"\t\t [❌-ERROR] delete_db_entry failed: {e}")
            self.conn.rollback()
            return False, str(e)

