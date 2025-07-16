import os
import pyodbc
import uuid


class DBManager:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
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

    def save_new_resume(self, UserId:str, ResumeName:str, FilePath:str, IsCurated:bool, ResumeJson:str):
        """
        Saves a new resume entry in the database.
        """
        try:
            ResumeId = str(uuid.uuid4())
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tblResume (Id, UserId, ResumeName, FilePath, IsCurated, ResumeJson) VALUES (?, ?, ?, ?, ?, ?)",
                ResumeId, UserId, ResumeName, FilePath, IsCurated, ResumeJson
            )
            conn.commit()
            print(f"Resume {FilePath} saved successfully for user {UserId}.")
        
        except Exception as e:
            print(f"Error saving resume: {e}")
        
        finally:
            cursor.close()
            conn.close()

    