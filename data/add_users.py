import os
import pyodbc
import uuid


class DBManager:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.connection_string = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-SC072N0\MSSQLSERVER01;DATABASE=pepper;Trusted_Connection=yes;'

    def add_user(self, name, Pin):
        """
        Adds a new user to the database.
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            user_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO tblUsers (Id, Name, Pin) VALUES (?, ?, ?)", user_id, name, Pin)
            conn.commit()
            return user_id
        except Exception as e:
            print(f"Error adding user: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":

    while True:
        name = input("Enter your name: ")
        pin = input("Enter your PIN: ")
        if len(pin) != 4 or not pin.isdigit():
            print("PIN must be a 4-digit number. Please try again.")
            continue
        
        db_manager = DBManager()
        user_id = db_manager.add_user(name, pin)
        
        if user_id:
            print(f"User added successfully with ID: {user_id}")
        else:
            print("Failed to add user. Please try again.")