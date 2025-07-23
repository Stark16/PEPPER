import os
import json
from docx import Document
import docx
from docx.text.run import Run
from typing import Dict, List
import docxedit  # Make sure this is installed
import sys
import copy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import model_llm

class WordFileManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sections = {}  # structured resume data
        self.formatting = {}  # global formatting metadata
        self.doc = None
        self.PATH_self_dir = os.path.join(os.path.dirname(__file__))
        self.OBJ_ModeLLM = model_llm.ModelLLM()
        self._get_known_sections(self.filepath)

    def _format_text(self, run: Run) -> str:
        text = run.text
        if run.bold and run.italic:
            return f"***{text}***"
        elif run.bold:
            return f"**{text}**"
        elif run.italic:
            return f"*{text}*"
        return text
    
    
    def docx_to_text(self, path: str) -> str:
        doc = docx.Document(path)
        return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    
    
    def _get_known_sections(self, docx_path: str) -> list[str]:
        """
        1. Reads a .docx resume.
        2. Sends the text to Gemini with a prompt that asks ONLY for section headers
        (including inferred 'SUMMARY' if no explicit title).
        3. Returns a Python list of headers in document order.
        """
        resume_text = self.docx_to_text(docx_path)

        system_prompt = {"role": "system", "content":  f"""
                        You will be given a resume document. Your task is to analyze its structure and return a list of section headers that are present in the resume.

                        Please return a JSON array of strings, where each string is a distinct section heading (e.g., "SUMMARY", "EDUCATION", "EXPERIENCE", etc.).

                        ⚠️ Important:
                        - Return headers in the order they appear in the document.
                        - If the resume starts with a paragraph that seems to be a self-description or overview, include "SUMMARY" even if no such title is present.

                        Only return the array, no explanation.
                        """}
        input_prompt = {"role": "user", "content":  f"""
                        RESUME TEXT:
                        \"\"\"{resume_text}\"\"\"
                        """}
        
        prompt = [system_prompt, input_prompt]
        output = self.OBJ_ModeLLM.query(prompt)

        # -- parse Gemini response safely ---------------------------------
        # Gemini might wrap the JSON in extra text or newlines,
        # so locate the first '[' and the last ']' just in case.
        raw = output.strip()
        start = raw.find('[')
        end   = raw.rfind(']') + 1
        header_list = json.loads(raw[start:end])

        # Ensure it's a list of uppercase strings (deduplicated, order kept)
        self.known_sections = []
        seen    = set()
        for h in header_list:
            h_upper = h.strip().upper()
            if h_upper and h_upper not in seen:
                self.known_sections.append(h_upper)
                seen.add(h_upper)


    def _get_section_name(self, para_text: str) -> str:

        cleaned = para_text.strip().upper()
        if cleaned in self.known_sections:
            return cleaned
        return None

    def read(self):
        self.doc = Document(self.filepath)
        current_section = None

        for para in self.doc.paragraphs:
            para_text = "".join([self._format_text(run) for run in para.runs])
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

    def mark_updates_for_docxedit(self, change_suggestions: dict):
        """
        Combine Agent‑5 suggestions into self.sections so write() can
        do in‑place replacements with docxedit.

        change_suggestions: the dict loaded from agent5_gemini.json
        """
        changes = change_suggestions.get("resume_changes", [])
        for change in changes:
            section = change.get("section")
            if section not in self.sections:
                print(f"[!] Section '{section}' not found, skipping.")
                continue

            content = self.sections[section]["content"]

            # ---------- replacements ----------
            if "replace" in change:
                orig = change["replace"].get("original", "").strip()
                upd  = change["replace"].get("updated", "").strip()
                matched = False
                for i, line in enumerate(content):
                    # Compare after stripping (Gemini returns trimmed text)
                    if line.strip() == orig:
                        # Preserve leading / trailing whitespace and tabs
                        prefix = line[:len(line) - len(line.lstrip())]
                        suffix = line[len(line.rstrip()):]
                        content[i] = f"{prefix}{orig}<updated>{upd}{suffix}"
                        matched = True
                        break
                if not matched:
                    print(f"[!] Could not find exact text in '{section}' for:\n{orig}\n")

            # ---------- deletions ----------
            if "delete" in change:
                to_del = change["delete"].strip()
                new_content = [ln for ln in content if ln.strip() != to_del]
                if len(new_content) == len(content):
                    print(f"[!] Could not find deletion target in '{section}':\n{to_del}\n")
                self.sections[section]["content"] = new_content

            print(json.dumps(self.sections, indent=2, ensure_ascii=False))

    
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
                        old, new = parts[0].strip(), parts[1]
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
    input_resume = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data/candidate_data/default_resumes/f4217103-e728-487c-aa93-8dcba245ef83.docx"
    # input_resume = r"data/candidate_data/default_resumes/Braunschweig Resume.docx"
    output_resume = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\candidate_data\curated_resumes\Pradyumn_Pathak_tesla.docx"

    # resume_json = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\resume_data.json"
    resume_json_updated = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\resume_data_updated.json"
    agent4_json = r"D:\Personal\Projects\Python_Projects\projects\PEPPER\data\agent5_gemini.json"

    with open(agent4_json, 'r', encoding='utf-8') as f:
        resume_coach_feedback = json.load(f)

    OBJ = WordFileManager(input_resume)
    OBJ.read()
    OBJ.mark_updates_for_docxedit(resume_coach_feedback)
    OBJ.export_json()
    OBJ.write(resume_json_updated)
