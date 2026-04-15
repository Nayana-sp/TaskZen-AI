from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from db import SessionLocal
import models


def check_tasks():
    db = SessionLocal()
    try:
        tasks = db.query(models.Task).filter(
            models.Task.status != "Completed",
            models.Task.reminder_sent == False
        ).all()

        for task in tasks:

            if task.reminder_time:
                try:
                    reminder_dt = task.reminder_time

                    if isinstance(reminder_dt, str):
                        reminder_dt = datetime.fromisoformat(reminder_dt)

                    if reminder_dt and reminder_dt <= datetime.utcnow():
                        print(f"🔔 Reminder: {task.task_name}")
                        task.reminder_sent = True
                        db.commit()

                except Exception as e:
                    print(f"⚠️ Invalid reminder format: {task.reminder_time}", e)

    except Exception as e:
        print(f" Scheduler error: {e}")

    finally:
        db.close()
def delete_completed_tasks():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        threshold = now - timedelta(hours=12)

        tasks = db.query(models.Task).filter(
            models.Task.status == "Completed",
            models.Task.completed_at != None,
            models.Task.completed_at < threshold
        ).all()

        for task in tasks:
            print(f"🗑 Deleting completed task: {task.task_name}")
            db.delete(task)

        db.commit()

    except Exception as e:
        print(f" Delete scheduler error: {e}")

    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_tasks, "interval", seconds=60)
scheduler.add_job(delete_completed_tasks, "interval", hours=1)
