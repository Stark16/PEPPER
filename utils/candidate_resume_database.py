import os

class CandidateResumeDatabase:

    def __init__(self):
        self.PATH_self_dir = os.path.dirname(os.path.realpath(__file__))
        self.PATH_db = os.path.join(self.PATH_self_dir, '../data/candidate_data')
        self.PATH_default_resumes = os.path.join(self.PATH_db, "default_resumes")
        self.PATH_curated_resumes = os.path.join(self.PATH_db, "curated_resumes")

        # Ensure all directories exist
        for path in [self.PATH_db, self.PATH_default_resumes, self.PATH_curated_resumes]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

    def save_resume_file(self, file_bytes: bytes, filename: str) -> str:
        """
        Save the uploaded resume file to the default_resumes folder with the given filename.
        Returns the full path to the saved file.
        """
        # Ensure the filename ends with .docx
        if not filename.lower().endswith('.docx'):
            filename += '.docx'
        save_path = os.path.join(self.PATH_default_resumes, filename)
        with open(save_path, 'wb') as f:
            f.write(file_bytes)
        return save_path

    def list_default_resumes(self):
        """Return a list of filenames in the default_resumes folder."""
        try:
            return [f for f in os.listdir(self.PATH_default_resumes) if os.path.isfile(os.path.join(self.PATH_default_resumes, f))]
        except Exception:
            return []

    def list_curated_resumes(self):
        """Return a list of filenames in the curated_resumes folder."""
        try:
            return [f for f in os.listdir(self.PATH_curated_resumes) if os.path.isfile(os.path.join(self.PATH_curated_resumes, f))]
        except Exception:
            return []

    def get_resume_file(self, filename: str, curated: bool = False) -> str:
        """
        Return the full path to the requested resume file from the appropriate folder.
        """
        folder = self.PATH_curated_resumes if curated else self.PATH_default_resumes
        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):
            return file_path
        else:
            return None
        
    def edit_resume(self, resume: dict, changes: dict) -> dict:
        """
        Dummy implementation: returns the resume and changes as if applied.
        Replace this with actual logic to edit a resume file as needed.
        """
        # In a real implementation, you would load the resume (from file),
        # apply the changes, and save it back. Here, just return both.
        return {
            "message": "Resume edited successfully",
            "resume": resume,
            "changes": changes
        }
    def delete_resume_file(self, filename: str, curated: bool = False) -> bool:
        """
        Delete the specified resume file from the appropriate folder.
        Returns True if deleted, False if not found or error.
        """
        folder = self.PATH_curated_resumes if curated else self.PATH_default_resumes
        file_path = os.path.join(folder, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                return False
        except Exception:
            return False