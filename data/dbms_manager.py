import os
import pyodbc
from utils.candidate_resume_database import CandidateResumeDatabase
import uuid


class DBManager:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.candidate_db = CandidateResumeDatabase()
        self.connection_string = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-SC072N0\MSSQLSERVER01;DATABASE=pepper;Trusted_Connection=yes;'

    def test_connection(self):
        """Test the database connection!"""

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                print("✅ Connection successful!")
                return True
            else:
                print("⚠️ Connected, but unexpected result:", result)
                return False

        except pyodbc.Error as e:
            print("❌ Connection failed:", e)
            return False
        finally:
            if 'conn' in locals():
                conn.close()

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

    def save_new_resume(self, UserId: str, ResumeName: str, file_bytes: bytes, IsCurated: bool, ResumeJson: str = None, candidate_db=None, created_on=None):
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
            rel_file_path = os.path.relpath(save_path, data_base)
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
            rel_file_path = row.FilePath
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
                WHERE r.UserId = ?
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
                if row.Status != 'finished':
                    # Count how many pending/processing requests were submitted before this one
                    queue_position = sum(1 for v in pending_dict.values() if v < row.CreatedOn)
                entry = {
                    'RequestId': row.Id,
                    'endpoint': row.Endpoint,
                    'status': 'Finished' if row.Status == 'finished' else queue_position + 1 if queue_position is not None else None,
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

    def fetch_user_resumes(self, UserId: str, is_curated: bool):
        """
        Fetches resumes for a user filtered by IsCurated, ordered by CreatedOn (latest first).
        Returns a list of dicts: {ResumeId, Name, HasJson}
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Id, ResumeName, ResumeJson FROM tblResume WHERE UserId = ? AND IsCurated = ? ORDER BY CreatedOn DESC",
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
                    "HasJson": has_json
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