# Personal Expense Tracker

Personal Expense Tracker that allows import/export and track transaction from on SMS

🚀 Motivation

- **This project was born out of a personal need when the expense tracker app I relied on reached its end-of-life and lost official support.**
- Instead of just looking for a commercial replacement, I used this as an opportunity to build my own solution, as part of my Zoomcamp project.

## Features

- Allow CSV import/export

## Future implementation

- Track transactions based on SMS

## 1. Setting Up the Target Environment

### Approach A: Desktop Containerized Engine (For Zoomcamp Peer Review)

To boot up the complete isolated environment containing the React frontend, FastAPI backend, and PostgreSQL engine:

```bash
docker-compose up --build
```

- **Web UI URL:** `http://localhost:3000`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`

### Approach B: Native Android Storage Hosting (Personal Use-Case)

To run everything directly on your mobile device inside **Termux** using local loopbacks and zero cloud dependencies:

1. Open Termux on Android and provision core dependencies:

   ```bash
   pkg update && pkg upgrade -y
   pkg install python nodejs-lts git -y
   ```

2. Clone your workspace and navigate into the `backend/` engine. Initialize your server natively (It automatically defaults to zero-dependency local SQLite file storage):

   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic requests
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Open a second Termux terminal frame, step into `frontend/`, launch a local preview or build static assets, and use mobile browsers (e.g., Chrome) to view `http://localhost:3000` and trigger **"Add to Home Screen"** to spin up your native installable standalone PWA app structure.

---

## 2. Local Tasker / MacroDroid Subsystem Dispatch Pipeline

To replace your out-of-support application with real-time tracking streams running straight into your Termux backend API, configure your mobile tracking scripts (like **MacroDroid**) with these exact rule variables:

- **Subsystem Event Trigger:** `SMS Received` ➔ `From Any Sender`
- **Execution Event Action:** `HTTP POST`
- **Target URL Destination:** `http://127.0.0.1:8000/api/v1/webhook/sms`
- **Request Content-Type:** `application/json`
- **Request Body Parameters Layout:**

  ```json
  {
    "sender": "{sms_number}",
    "text": "{sms_body}",
    "timestamp": "{date_time_iso}"
  }
  ```
