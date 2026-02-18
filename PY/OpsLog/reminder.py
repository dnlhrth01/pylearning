from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

scheduler = BackgroundScheduler()
scheduler.start()


def reminder_message(message: str):
    print(f"🔔 REMINDER: {message} | {datetime.now()}")


def set_reminder(run_time, message: str):
    scheduler.add_job(
        reminder_message,
        'date',
        run_date=run_time,
        args=[message]
    )
