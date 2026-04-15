from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel
from scheduler import scheduler
import models
import auth
from db import engine, get_db
import nlp_engine


# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ─── DB Init ──────────────────────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

# Safely add user_id column to voice_logs if it doesn't exist
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE voice_logs ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        conn.commit()
    except Exception:
        pass # Column likely already exists

# ─── App ──────────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not scheduler.running:
        scheduler.start()
        logging.info("Background scheduler started.")
    logging.info("Warming up NLP models...")
    nlp_engine.get_nlp_models()
    logging.info("NLP models ready.")
    yield

app = FastAPI(title="Voice Planner API", lifespan=lifespan)




app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    with open("error_log.txt", "a") as f:
        f.write("\n--- Unhandled Exception ---\n")
        f.write(traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=models.UserResponse)
def register(user: models.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/auth/login", response_model=models.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=models.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ─── TASKS ────────────────────────────────────────────────────────────────────

@app.get("/api/tasks", response_model=list[models.TaskResponse])
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    tasks = db.query(models.Task).filter(models.Task.user_id == current_user.id).all()

    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "priority": task.priority,
            "date": str(task.date) if task.date else None,
            "time": task.time,
            "reminder_time": task.reminder_time,
            "user_id": task.user_id,
            "created_at": task.created_at,       
            "completed_at": task.completed_at  
        })

    return result

@app.post("/api/tasks", response_model=models.TaskResponse)
def create_task(task: models.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_task = models.Task(**task.dict(), user_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"status": "success", "message": "Task deleted"}


@app.put("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "Completed":
        task.status = "Pending"
        task.completed_at = None
        message = "Marked as pending"
    else:
        task.status = "Completed"
        task.completed_at = datetime.utcnow()
        message = "Marked as completed"

    db.commit()
    return {"status": "success", "message": message}


# ─── VOICE ────────────────────────────────────────────────────────────────────

class VoiceProcessRequest(BaseModel):
    transcript: str


@app.post("/api/voice/process")
def process_voice(
    req: VoiceProcessRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    transcript = req.transcript.strip()

    if not transcript:
        raise HTTPException(status_code=400, detail="Empty command")
    if len(transcript) > 500:
        raise HTTPException(status_code=400, detail="Command too long")

    logging.info(f"Voice input from user {current_user.id}: {transcript}")

    try:
        parsed_data = nlp_engine.parse_voice_command(transcript)
    except Exception as e:
        import traceback
        logging.error(f"NLP failed with exception: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="NLP failed")

    # BUG FIX: VoiceLog was created without user_id, making it impossible to
    # know which user issued which command. Now correctly stores current_user.id.
    db.add(models.VoiceLog(
        user_id=current_user.id,
        command_text=transcript,
        extracted_intent=parsed_data.get("intent"),
        extracted_entities=parsed_data.get("task_name")
    ))
    db.commit()

    if parsed_data.get("needs_confirmation"):
        return {
            "status": "confirm",
            "message": parsed_data.get("sentence"),
            "data": parsed_data
        }

    return execute_nlp_action(parsed_data, db, current_user)


@app.post("/api/voice/confirm")
def confirm_voice(
    parsed_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return execute_nlp_action(parsed_data, db, current_user)


# ─── NLP EXECUTION ────────────────────────────────────────────────────────────

def execute_nlp_action(parsed_data: dict, db: Session, current_user: models.User):
    intent    = parsed_data.get("intent")
    task_name = parsed_data.get("task_name", "").lower()
    reply     = parsed_data.get("sentence")

    tasks = db.query(models.Task).filter(models.Task.user_id == current_user.id).all()

    if intent == "delete_task":
        for t in tasks:
            if t.task_name.lower() == task_name:
                db.delete(t)
                db.commit()
                # BUG FIX: Include `data` key so the frontend result card can render.
                return {"status": "success", "message": f"Deleted: {t.task_name}", "data": parsed_data}
        return {"status": "error", "message": "Task not found", "data": parsed_data}

    elif intent == "complete_task":
        for t in tasks:
            if t.task_name.lower() == task_name:
                t.status = "Completed"
                t.completed_at = datetime.utcnow()
                db.commit()
                # BUG FIX: Include `data` key.
                return {"status": "success", "message": f"Completed: {t.task_name}", "data": parsed_data}
        return {"status": "error", "message": "Task not found", "data": parsed_data}

    else:
        # ADD TASK
        date_str     = parsed_data.get("date")
        time_str     = parsed_data.get("time")
        reminder_str = parsed_data.get("reminder_time")

        reminder_obj = None

        try:
            if reminder_str:
                reminder_obj = datetime.fromisoformat(reminder_str)
        except Exception as e:
            print("Reminder parse error:", e)

        if not date_str:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        new_task = models.Task(
            user_id=current_user.id,
            task_name=parsed_data.get("task_name") or "Untitled Task",
            date=date_str,
            time=time_str,
            reminder_time=reminder_obj,
            priority=parsed_data.get("priority", "Medium")
        )
        db.add(new_task)
        db.commit()

        # BUG FIX: Previously returned no `data` field. VoiceAI.jsx calls
        # setParsedData(response.data.data) — without this field the result card
        # had nothing to render. Now included for all three intent branches.
        return {
            "status": "success",
            "message": reply or "Task created successfully",
            "data": parsed_data
        }




