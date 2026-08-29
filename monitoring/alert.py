import logging as log
import datetime as dt
import requests, os, dotenv, time, socket
import psutil
from pathlib import Path

import db

dotenv.load_dotenv(Path(__file__).parent / ".env")

HOSTNAME = socket.gethostname()

SEVERITY_COLOR = {
    "warning": 0xF1C40F,   # yellow
    "critical": 0xC0392B,  # red
    "recovery": 0x2ECC71,  # green
}

SEVERITY_MENTION = {
    "warning": "",
    "critical": "@here",
}


def boot_time_check():
    '''A function that detects whether the current boot time has changed
    from the reboot time stored in the state database.'''
    boot_time = dt.datetime.fromtimestamp(psutil.boot_time())
    last_boot = db.get_state("last_boot")

    if last_boot is None:
        return True

    return dt.datetime.fromisoformat(last_boot) != boot_time


def update_boot_time():
    '''A function that saves the current boot time to the state database.'''
    boot_time = dt.datetime.fromtimestamp(psutil.boot_time())
    db.set_state("last_boot", boot_time.isoformat())


def discord_format(items, mode="alert"):
    '''A function that defines the Discord transmission format.
    mode: "alert" for new/ongoing problems, "recovery" for resolved problems.'''
    if mode == "recovery":
        color = SEVERITY_COLOR["recovery"]
        title = "SERVER MONITORING SYSTEM - RESOLVED"
        description = f"**{len(items)}** issue(s) have returned to normal."
        mention = ""
    else:
        highest = "critical" if any(i["severity"] == "critical" for i in items) else "warning"
        color = SEVERITY_COLOR[highest]
        title = "SERVER MONITORING SYSTEM"
        description = f"Detected **{len(items)}** issue(s) requiring attention."
        mention = SEVERITY_MENTION[highest]

    fields = [
        {
            "name": f"[{item['severity'].upper()}] {item['key']}" if mode == "alert" else item["key"],
            "value": f"```{item['message']}```",
            "inline": False,
        }
        for item in items
    ]

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {"text": f"{HOSTNAME} · Reported at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
    }

    payload = {"embeds": [embed]}
    if mention:
        payload["content"] = mention

    return payload


def send_message(message, retries=3, backoff=5):
    '''A function that sends messages to a Discord server, retrying on failure
    and falling back to a critical log entry if every attempt fails.'''
    web_hook = os.getenv("DISCORD_WEBHOOK")
    if not web_hook:
        log.error("There is no 'DISCORD_WEBHOOK' setting in the .env file.")
        return False

    for attempt in range(1, retries + 1):
        try:
            req = requests.post(web_hook, json=message, timeout=10)
            if req.status_code in (200, 204):
                log.info("Discord notification sent successfully.")
                return True
            log.error(f"Discord notification send failed (status code: {req.status_code}), attempt {attempt}/{retries}")
        except requests.exceptions.RequestException as e:
            log.error(f"Discord request exception occurred: {e} (attempt {attempt}/{retries})")

        if attempt < retries:
            time.sleep(backoff * attempt)

    log.critical(f"Discord notification failed after {retries} attempts. Message dropped: {message}")
    return False


def send_alert_batch(items):
    '''A function that sends a batch of new/ongoing problem items and records them in alert history.'''
    if not items:
        return

    message = discord_format(items, mode="alert")
    if send_message(message):
        for item in items:
            db.record_alert(item["key"], item["severity"], item["message"])


def send_recovery_batch(items):
    '''A function that sends a batch of resolved items.'''
    if not items:
        return

    message = discord_format(items, mode="recovery")
    if send_message(message):
        for item in items:
            db.record_alert(item["key"], "recovery", item["message"])


def send_heartbeat():
    '''A function that pings an external dead man's switch (e.g. healthchecks.io)
    so a third party can detect if this daemon stops running.'''
    url = os.getenv("HEALTHCHECK_URL")
    if not url:
        return

    try:
        requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        log.error(f"Heartbeat ping failed: {e}")


def send_weekly_summary():
    '''A function that builds and sends a weekly digest of resource usage,
    then prunes old metric history to keep the database small.'''
    from config import DISK_TREND_WINDOW_DAYS
    from check import security_updates_check

    history = db.get_metric_history("disk_usage", 7)
    if history:
        values = [v for _, v in history]
        avg_disk = sum(values) / len(values)
        summary_text = f"Average disk usage this week: {avg_disk:.1f}%"
    else:
        summary_text = "No metric history recorded this week."

    security_count = security_updates_check()
    if security_count is not None:
        summary_text += f"\nPending security updates: {security_count}"

    embed = {
        "title": "SERVER MONITORING SYSTEM - WEEKLY SUMMARY",
        "description": summary_text,
        "color": 0x3498DB,
        "footer": {"text": f"{HOSTNAME} · Reported at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
    }
    send_message({"embeds": [embed]})
    
    db.prune_metric_history(DISK_TREND_WINDOW_DAYS)
