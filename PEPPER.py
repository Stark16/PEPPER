
from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from utils.candidate_resume_database import CandidateResumeDatabase
from agents.jrms.agent3 import Agent3Recruiter

app = FastAPI()

# Enable CORS for all origins, methods, and headers (credentials must be False for allow_origins=['*'])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def initialize():
    info = []
    global db, agent3
    db = None
    agent3 = None
    try:
        db = CandidateResumeDatabase()
        info.append("CandidateResumeDatabase initialized successfully.")
    except Exception as e:
        info.append(f"CandidateResumeDatabase failed: {e}")
    try:
        agent3 = Agent3Recruiter()
        info.append("Agent3Recruiter initialized successfully.")
    except Exception as e:
        info.append(f"Agent3Recruiter failed: {e}")
    for msg in info:
        print(msg)

initialize()

@app.get("/")
async def home():
    return PlainTextResponse("PEPPER ready to assist")

@app.post("/resume/tailor")
async def tailor_resume(profile: dict = None, job: dict = None):
    # Dummy implementation
    return JSONResponse({"message": "Resume tailored successfully", "profile": profile, "job": job})

@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...), name: str = Form(...)):
    content = await file.read()
    # Save the file using the database utility
    save_path = db.save_resume_file(content, name)
    return JSONResponse({"filename": name, "size": len(content), "saved_to": save_path})

# Returns names of all resumes in default directory

@app.api_route("/resume/fetch/default", methods=["GET", "OPTIONS"])
async def fetch_default_resumes(request: Request):
    if request.method == "OPTIONS":
        return JSONResponse({}, status_code=200)
    resumes = db.list_default_resumes()
    return JSONResponse({"default_resumes": resumes})

# Returns names of all resumes in curated directory

@app.api_route("/resume/fetch/curated", methods=["GET", "OPTIONS"])
async def fetch_curated_resumes(request: Request):
    if request.method == "OPTIONS":
        return JSONResponse({}, status_code=200)
    resumes = db.list_curated_resumes()
    return JSONResponse({"curated_resumes": resumes})

# Download a resume file (default or curated)
@app.get("/resume/download")
async def download_resume(name: str, curated: bool = False):
    file_path = db.get_resume_file(name, curated)
    if file_path:
        return FileResponse(path=file_path, filename=name, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    return JSONResponse({"error": "File not found"}, status_code=404)

@app.post("/resume/edit")
async def edit_resume(resume: dict = None, changes: dict = None):
    result = db.edit_resume(resume, changes)
    return JSONResponse(result)

@app.delete("/resume/delete")
async def delete_resume(name: str = Query(...), curated: bool = Query(False)):
    success = db.delete_resume_file(name, curated)
    if success:
        return JSONResponse({"message": f"Resume '{name}' deleted successfully.", "curated": curated})
    else:
        return JSONResponse({"error": f"Resume '{name}' not found or could not be deleted.", "curated": curated}, status_code=404)
if __name__ == "__main__":
    print("PEPPER ready to assist")
    uvicorn.run("PEPPER:app", host="0.0.0.0", port=8000, reload=True)
