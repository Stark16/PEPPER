import os
import json
from docx import Document
from docx.text.run import Run
from typing import Dict, List
import docxedit  # Make sure this is installed

class WordFileManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sections = {}  # structured resume data
        self.formatting = {}  # global formatting metadata
        self.doc = None
        self.PATH_self_dir = os.path.join(os.path.dirname(__file__))

    def _format_text(self, run: Run) -> str:
        text = run.text
        if run.bold and run.italic:
            return f"***{text}***"
        elif run.bold:
            return f"**{text}**"
        elif run.italic:
            return f"*{text}*"
        return text

    def _get_section_name(self, para_text: str) -> str:
        known_sections = ["SUMMARY", "EXPERIENCE", "RESEARCH EXPERIENCE", "EDUCATION", "PROJECTS", "SKILLS"]
        cleaned = para_text.strip().upper()
        if cleaned in known_sections:
            return cleaned
        return None

    def read(self):
        self.doc = Document(self.filepath)
        current_section = None

        for para in self.doc.paragraphs:
            para_text = "".join([self._format_text(run) for run in para.runs]).strip()
            if not para_text:
                continue

            section = self._get_section_name(para_text)
            if section:
                current_section = section
                self.sections[current_section] = {
                    "content": [],
                    "formatting": {
                        "font_size": para.runs[0].font.size.pt if para.runs[0].font.size else None,
                        "bold": para.runs[0].bold,
                        "italic": para.runs[0].italic
                    }
                }
                continue

            if current_section:
                self.sections[current_section]["content"].append(para_text)

    def write(self, output_path: str):
        """
        Uses docxedit to replace existing content without breaking formatting.
        Assumes original file still exists and edits in-place.
        """
        doc = Document(self.filepath)
        replacements_made = 0

        for section, data in self.sections.items():
            for item in data["content"]:
                if "<updated>" in item:  # convention for marking updated lines
                    parts = item.split("<updated>")
                    if len(parts) == 2:
                        old, new = parts[0].strip(), parts[1].strip()
                        try:
                            docxedit.replace_string(doc, old_string=old, new_string=new)
                            replacements_made += 1
                        except Exception as e:
                            print(f"[!] Could not replace:\n'{old}' ➝ '{new}'\nError: {e}")

        doc.save(output_path)
        print(f"[+] Updated {replacements_made} item(s) in '{output_path}'")

    def export_json(self, output_path: str = None):
        """
        If output_path is provided, saves the JSON to file. Otherwise, returns the JSON as a Python dict.
        """
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(self.sections, f, indent=4)
        else:
            return self.sections


if __name__ == "__main__":
    input_resume = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\candidate_data\default_resumes\Pradyumn_Pathak_Resume.docx"
    output_resume = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\candidate_data\default_resumes\Pradyumn_Pathak_Resume_curated.docx"
    output_json = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\resume_data.json"

    OBJ = WordFileManager(input_resume)
    OBJ.read()
    OBJ.export_json(output_json)
    OBJ.write(output_resume)
