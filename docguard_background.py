from datetime import date, datetime
from pathlib import Path
import subprocess
import sys

import docguard_database as db

try:
    from plyer import notification
except ImportError:
    notification = None

BASE_DIR = Path(__file__).resolve().parent
TASK_NAME = "DocGuard Expiry Notifications"


def send_notification(document, days_left):
    name = document["name"]
    if days_left == 0:
        title = "DocGuard — Document Expires Today"
        message = f"{name} expires today. Please renew it immediately."
    elif days_left == 1:
        title = "DocGuard — Document Expires Tomorrow"
        message = f"{name} expires tomorrow. Please renew it."
    else:
        title = "DocGuard — Expiry Reminder"
        message = f"{name} expires in {days_left} days. Please renew it before expiry."
    if notification:
        try:
            notification.notify(title=title, message=message, app_name="DocGuard", timeout=10)
        except Exception as error:
            print("Notification failed:", error)


def check_expiries():
    db.initialize()
    today = date.today()
    today_string = today.isoformat()
    sent = 0
    for document in db.get_all_documents_for_notifications():
        expiry = document["expiry_date"]
        if not expiry:
            continue
        try:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_left = (expiry_date - today).days
        if 0 <= days_left <= 7 and document["last_notification_date"] != today_string:
            send_notification(document, days_left)
            db.mark_notification_sent(document["id"], today_string)
            sent += 1
    return sent


def install_windows_task():
    if not sys.platform.startswith("win"):
        return False, "Background Task Scheduler is only supported on Windows."
    python_exe = Path(sys.executable)
    if python_exe.name.lower() == "python.exe":
        pythonw = python_exe.with_name("pythonw.exe")
        if pythonw.exists():
            python_exe = pythonw
    script = BASE_DIR / "docguard_background.py"
    task_command = f'"{python_exe}" "{script}" --run'
    command = [
        "schtasks", "/Create", "/TN", TASK_NAME,
        "/SC", "DAILY", "/ST", "09:00",
        "/TR", task_command, "/F", "/RL", "LIMITED"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return True, "Background expiry notifications are enabled."
        return False, result.stderr.strip() or result.stdout.strip()
    except Exception as error:
        return False, str(error)


def remove_windows_task():
    if not sys.platform.startswith("win"):
        return False
    result = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True, text=True)
    return result.returncode == 0


if __name__ == "__main__":
    if "--install" in sys.argv:
        ok, message = install_windows_task()
        print(message)
        raise SystemExit(0 if ok else 1)
    check_expiries()
