# PEPPER API Documentation

This document provides a detailed reference for all REST API endpoints exposed by `PEPPER.py`. It is intended for frontend developers and integrators. All endpoints are served from the FastAPI app and return JSON responses unless otherwise noted.

---

## General Notes
- All endpoints return JSON with explicit `success` or `error` keys where relevant.
- Most IDs are strings (UUIDs).
- All date/time values are returned as ISO 8601 strings.
- Resume and agent outputs may include nested JSON objects.
- All endpoints support CORS for cross-origin requests.

---

## Endpoints

### 1. `GET /`
**Description:**
- Health check endpoint. Returns a plain text message.

**Response:**
- `200 OK`: `"PEPPER ready to assist"` (plain text)

---

### 2. `GET /users`
**Description:**
- Fetches all user names in the system.

**Response:**
- `200 OK`: `{ "users": [string, ...] }`

---

### 3. `POST /login`
**Description:**
- Authenticates a user by name and 4-digit PIN.

**Request (form-data):**
- `Name` (string, required)
- `Pin` (string, required, 4 digits)

**Response:**
- `200 OK`: `{ "success": true, "Id": string }` (on success)
- `200 OK`: `{ "success": false }` (on failure)
- `400 Bad Request`: `{ "success": false, "error": "Pin must be a 4-digit number." }`

---

### 4. `POST /user/fetch/request`
**Description:**
- Fetches paginated request entries for a user, including endpoint, status, and resume name.

**Request (JSON body):**
```
{
  "user_id": string,      // required
  "page_num": int,        // required, 1-based
  "n": int                // required, number of entries per page
}
```

**Response:**
- `200 OK`: `{ "requests": [ { "RequestId": string, "endpoint": string, "status": string|int, "resumeName": string|null }, ... ] }`
- `400 Bad Request`: `{ "error": "user_id, page_num, and n are required." }`

---

### 5. `POST /user/fetch/request/state`
**Description:**
- Fetches the status and agent outputs for a specific request.

**Request (JSON body):**
```
{
  "request_id": string    // required
}
```

**Response:**
- `200 OK`: `{ "success": true, "status": string, "agents": { "Agent2": JSON|null, "Agent3": JSON|null, "Agent4": JSON|null, "Agent5": string|null } }`
  - Note: `Agent5` is always a string (JSON-serialized if originally an object), or null if not present.
- `404 Not Found`: `{ "success": false, "error": string }`
- `400 Bad Request`: `{ "detail": "request_id is required." }`

---

### 6. `POST /user/request/delete`
**Description:**
- Soft deletes a user request entry from the database (sets IsDelete=1 for the given request).

**Request (JSON body):**
```
{
  "request_id": string   // Required. The unique RequestId to delete.
}
```

**Response:**
- `200 OK`: `{ "success": true }`
- `500 Internal Server Error`: `{ "success": false, "error": string }`
- `400 Bad Request`: `{ "success": false, "error": "request_id is required." }`

---

### 7. `POST /user/download/curated`
**Description:**
- Downloads a curated resume file by request_id. Returns the .docx file associated with the curated resume for the given request.

**Request (JSON body):**
```
{
  "request_id": "string"   // Required. The unique RequestId for the curated resume.
}
```

**Response:**
- `200 OK`: Returns the .docx file as an attachment (with correct filename and MIME type)
- `404 Not Found`: `{ "error": "Curated resume not found." }`
- `400 Bad Request`: `{ "error": "request_id is required." }`

---

### 8. `POST /resume/upload`
**Description:**
- Uploads a new resume or updates an existing one. Accepts file upload and metadata.

**Request (multipart/form-data):**
- `user_id` (string, required)
- `file` (file, required, .docx)
- `file_name` (string, required, will be forced to .docx)
- `ResumeId` (string, optional, if updating existing resume)

**Response:**
- `200 OK`: `{ "success": true, "resume_id": string, "message": string }`
- `500 Internal Server Error`: `{ "success": false, "error": string }`

---

### 9. `GET /resume/download`
**Description:**
- Downloads a resume file by ResumeId.

**Request (query params):**
- `ResumeId` (string, required)

**Response:**
- `200 OK`: Returns the .docx file as an attachment (with correct filename and MIME type)
- `404 Not Found`: `{ "error": "Resume not found." }`

---

### 10. `POST /resume/rename`
**Description:**
- Renames a resume in the database.

**Request (form-data):**
- `ResumeId` (string, required)
- `new_name` (string, required)

**Response:**
- `200 OK`: `{ "success": true, "message": "Resume renamed successfully." }`
- `500 Internal Server Error`: `{ "success": false, "error": "Failed to rename resume." }`

---

### 11. `POST /resume/list`
**Description:**
- Lists all resumes for a user, filtered by curated status.

**Request (form-data):**
- `user_id` (string, required)
- `mode` (string, optional, default: "default"; set to "curated" for curated resumes)

**Response:**
- `200 OK`: `{ "resumes": [ { "ResumeId": string, "Name": string, "HasJson": bool }, ... ] }`

---

### 12. `POST /resume/curate`
**Description:**
- Creates a curated resume entry and queues a curation request.

**Request (JSON body):**
```
{
  "resume_id": string,    // required
  "user_id": string,      // required
  "job_desc": JSON        // required, job description object
}
```

**Response:**
- `200 OK`: `{ "success": true, "curated_resume_id": string, "message": "Curated resume created and request queued." }`
- `500 Internal Server Error`: `{ "success": false, "error": string }`
- `400 Bad Request`: `{ "success": false, "error": "resume_id, user_id, and job_desc are required." }`

---

### 13. `POST /resume/delete`
**Description:**  
Deletes a resume entry from the database and removes the associated file if present.

**Request (JSON body):**
```
{
  "resume_id": "string"   // Required. The unique ResumeId to delete.
}
```

**Response:**
- `200 OK`: `{ "success": true }`
- `500 Internal Server Error`: `{ "success": false, "error": string }`
- `400 Bad Request`: `{ "success": false, "error": "resume_id is required." }`

---

### 14. `POST /user/request/approve`
**Description:**
- Approves or rejects a request by updating its status. Optionally, you can provide `agent4_updated` data.

**Request (JSON body):**
```
{
  "request_id": string,   // required
  "approve": bool,        // required, true for approve, false for reject
  "agent4_updated": JSON  // optional, updated agent4 data
}
```

**Response:**
- `200 OK`: `{ "success": true, "message": "Request approved."|"Request rejected." }`
- `500 Internal Server Error`: `{ "success": false, "error": string }`
- `400 Bad Request`: `{ "success": false, "error": "request_id and approve are required." }`

---

## Data Types
- All IDs: string (UUID)
- Dates: string (ISO 8601)
- Resume JSON: JSON object
- Agent outputs: JSON object or null
- Status: string (e.g., "queued", "pending", "finished", "approved", "rejected")
- Boolean: true/false
- Integers: for pagination, etc.

---

## Error Handling
- All endpoints return a JSON object with an `error` or `success: false` key and a descriptive message on failure.
- HTTP status codes are used appropriately (400 for bad request, 404 for not found, 500 for server error).

---

## Example: Fetch User Requests
**Request:**
```
POST /user/fetch/request
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "page_num": 1,
  "n": 10
}
```
**Response:**
```
{
  "requests": [
    {
      "RequestId": "...",
      "endpoint": "/curate_resume",
      "status": 1,
      "resumeName": "MyResume.docx"
    },
    ...
  ]
}
```

---

## Contact
For questions or integration help, contact the backend team.
