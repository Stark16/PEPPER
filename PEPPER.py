# Fetch user requests with queue position and resume name
from fastapi import Body
from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from utils.candidate_resume_database import CandidateResumeDatabase
from agents.agent3 import Agent3Recruiter
from agents.agent2 import Agent2VirtualMe
from agents.agent4 import Agent4CareerAdvisor
from data.dbms_manager import DBManager

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
    global db, agent3, agent2, agent4, dbms
    db = None
    agent3 = None
    agent2 = None
    agent4 = None
    dbms = None
    try:
        db = CandidateResumeDatabase()
        info.append("CandidateResumeDatabase initialized successfully.")
    except Exception as e:
        info.append(f"CandidateResumeDatabase failed: {e}")
    # try:
    #     agent3 = Agent3Recruiter()
    #     info.append("Agent3Recruiter initialized successfully.")
    # except Exception as e:
    #     info.append(f"Agent3Recruiter failed: {e}")
    # try:
    #     agent2 = Agent2VirtualMe()
    #     info.append("Agent2VirtualMe initialized successfully.")
    # except Exception as e:
    #     info.append(f"Agent2VirtualMe failed: {e}")
    # try:
    #     agent4 = Agent4CareerAdvisor()
    #     info.append("Agent4CareerAdvisor initialized successfully.")
    # except Exception as e:
    #     info.append(f"Agent4CareerAdvisor failed: {e}")
    try:
        dbms = DBManager()
        info.append("DBManager initialized successfully.")
        # Test DB connection
        if dbms.test_connection() == False:
            print("Database connection failed. Server initialization terminated.")
            import sys; sys.exit(1)
    except Exception as e:
        info.append(f"DBManager failed: {e}")
        print("Database connection failed. Server initialization terminated.")
        import sys; sys.exit(1)
    for msg in info:
        print(msg)

initialize()

@app.get("/")
async def home():
    return PlainTextResponse("PEPPER ready to assist")

# API to fetch all user names
@app.get("/users")
async def get_users():
    users = dbms.fetch_all_user_names()
    return JSONResponse({"users": users})

# Login API
@app.post("/login")
async def login(Name: str = Form(...), Pin: str = Form(...)):
    # Pin should be a 4-digit string
    if not (Pin.isdigit() and len(Pin) == 4):
        return JSONResponse({"success": False, "error": "Pin must be a 4-digit number."}, status_code=400)
    success, user_id = dbms.verify_user_pin(Name, Pin)
    if success:
        return JSONResponse({"success": True, "Id": user_id})
    else:
        return JSONResponse({"success": False})

@app.post("/user/fetch/request")
async def fetch_user_requests(payload: dict = Body(...)):
    user_id = payload.get("user_id")
    page_num = payload.get("page_num")
    n = payload.get("n")
    if not user_id or not isinstance(page_num, int) or not isinstance(n, int):
        return JSONResponse({"error": "user_id, page_num, and n are required."}, status_code=400)
    entries = dbms.fetch_user_requests(user_id, page_num, n)
    print(entries)
    return JSONResponse({"requests": entries})

@app.post("/resume/upload")
async def upload_resume(user_id: str = Form(...), file: UploadFile = File(...), file_name: str = Form(...), ResumeId: str = Form(None)):
    # Ensure file_name ends with .docx
    if not file_name.lower().endswith('.docx'):
        file_name += '.docx'
    try:
        file_bytes = await file.read()
        if ResumeId:
            # Update existing resume file and name
            success, result = dbms.update_resume_file(
                ResumeId=ResumeId,
                ResumeName=file_name,
                file_bytes=file_bytes,
                candidate_db=db
            )
            action = "updated"
        else:
            # Use the original file_name for display, but save as ResumeId.docx
            success, result = dbms.save_new_resume(
                UserId=user_id,
                ResumeName=file_name,
                file_bytes=file_bytes,
                IsCurated=False,
                ResumeJson=None,
                candidate_db=db
            )
            action = "uploaded and request created"
        if not success:
            return JSONResponse({"success": False, "error": result}, status_code=500)
        return JSONResponse({"success": True, "resume_id": result, "message": f"Resume {action}."})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    
@app.get("/resume/download")
async def download_resume(ResumeId: str = Query(...)):
    abs_file_path, resume_name = dbms.get_resume_file_info(ResumeId)
    import os
    if not abs_file_path or not os.path.exists(abs_file_path):
        return JSONResponse({"error": "Resume not found."}, status_code=404)
    return FileResponse(
        path=abs_file_path,
        filename=resume_name,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    
@app.post("/resume/rename")
async def rename_resume(ResumeId: str = Form(...), new_name: str = Form(...)):
    success = dbms.rename_resume(ResumeId, new_name)
    if success:
        return JSONResponse({"success": True, "message": "Resume renamed successfully."})
    else:
        return JSONResponse({"success": False, "error": "Failed to rename resume."}, status_code=500)

@app.post("/resume/list")
async def list_resumes(user_id: str = Form(...), mode: str = Form("default")):
    # mode: "default" or "curated"
    is_curated = True if mode.lower() == "curated" else False
    resumes = dbms.fetch_user_resumes(user_id, is_curated)
    return JSONResponse({"resumes": resumes})


if __name__ == "__main__":
    print("PEPPER ready to assist")
    uvicorn.run("PEPPER:app", host="0.0.0.0", port=8000, reload=True)
