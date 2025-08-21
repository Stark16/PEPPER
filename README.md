
# PEPPER

**PEPPER** (Python Enhanced Professional Profile & Employment Recommender) is an advanced, agentic-AI powered platform for automatic job application, resume analysis, and career guidance. It streamlines the job search and application process by leveraging multiple specialized AI agents to analyze resumes, extract insights, match candidates to jobs, and provide actionable feedback for career growth.

---

## 🚀 Key Features

- **Automated Resume Parsing:** Upload your resume (DOCX), and PEPPER converts it into structured JSON for downstream analysis.
- **Multi-Agent Analysis:** Four specialized AI agents (VirtualMe, Recruiter, Career Advisor, Resume Coach) collaborate to review, critique, and enhance your resume for specific job targets.
- **Job Description Matching:** Extracts must-have and good-to-have skills from job descriptions, simulates recruiter and ATS (Applicant Tracking System) screening.
- **Personalized Career Feedback:** Section-wise, actionable suggestions to improve your resume and align it with your career goals or job postings.
- **End-to-End Workflow:** From resume upload to job matching and resume editing suggestions, all steps are automated and traceable.
- **API-First Design:** Exposes endpoints for integration with other platforms or automation scripts.
- **Data Privacy:** All processing is local; your resumes and job data are not sent to third-party servers.

---

## 🧠 The PEPPER Agents

PEPPER uses a modular, agent-based architecture. Each agent is an expert in a specific aspect of the job application process:

- **Agent 2: VirtualMe**
	- Acts as a fast, analytical hiring manager.
	- Reads your resume and outputs a professional summary, strengths, and style analysis in JSON.

- **Agent 3: Recruiter**
	- Simulates a real recruiter and an ATS.
	- Analyzes job descriptions to extract must-have/good-to-have skills and ATS keywords.

- **Agent 4: Career Advisor**
	- Acts as a career coach.
	- Compares your resume (and Agent 2/3 outputs) to the job description, providing section-wise, actionable edit instructions to improve alignment.

- **Agent 5: Resume Coach**
	- Synthesizes all feedback and generates a final set of resume changes, ready for editing or direct application.

---

## 🛠️ Supported Workflows

1. **Resume Upload & Parsing:**
	 - Upload your resume (DOCX). PEPPER parses and converts it to structured JSON.
2. **AI Agent Analysis:**
	 - VirtualMe analyzes your resume for strengths and style.
	 - Recruiter/ATS analyzes job descriptions for requirements and keywords.
	 - Career Advisor compares your resume to job targets and suggests edits.
	 - Resume Coach synthesizes all feedback for final actionable changes.
3. **API Access:**
	 - Interact with PEPPER via RESTful API endpoints (FastAPI backend).
4. **Data Management:**
	 - All data is stored locally for privacy and traceability.

---

## 💡 Technologies Used (Brief)

- **Python 3.12**
- **FastAPI** for backend API
- **Multiprocessing** for parallel agent execution
- **Custom LLM Integration** (ModelLLM)
- **Document Parsing:** python-docx, custom logic
- **JSON-based Data Exchange** between agents

---

## 📁 Project Structure (Simplified)

```
PEPPER/
├── main.py                # Entry point for launching server and worker
├── PEPPER.py              # FastAPI backend and agent orchestration
├── agents/                # All agent logic (VirtualMe, Recruiter, Career Advisor, Resume Coach)
├── utils/                 # Resume parsing, LLM interface, helpers
├── data/                  # Local data storage (resumes, job descriptions, agent outputs)
├── README.md              # This file
```

---

## 📣 Why PEPPER?

- **For Job Seekers:** Get expert-level, AI-driven feedback on your resume and job fit, instantly.
- **For Developers:** Modular, extensible, and privacy-focused. Integrate with your own tools or extend with new agents.

---

## 📬 Getting Started

1. Clone the repo and install requirements (see `requirements.txt`).
2. Run `main.py` to launch the server and worker.
3. Use the API or UI to upload resumes and job descriptions.
4. Review agent feedback and apply suggested changes.

---

## 📝 License

See [LICENSE](LICENSE) for details.
