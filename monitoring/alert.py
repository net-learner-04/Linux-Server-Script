import logging as log
import datetime as dt
import requests, os, dotenv, sys

from config import ALERTFILE, COOLDOWN

dotenv.load_dotenv()


def last_alert_check():
    '''A function to check the last time a Discord notification was sent.'''
    if not os.path.exists(ALERTFILE):
        return True
    
    with open(ALERTFILE, mode="r") as file:
        last = dt.datetime.fromisoformat(file.read().strip())

    return (dt.datetime.now() - last).total_seconds() / 60 >= COOLDOWN


def update_last_alert():
    '''Function to update the last transmission time.'''
    with open(ALERTFILE, mode="w") as file:
        file.write(f"{dt.datetime.now().isoformat()}\n") 


def discord_format(warn_list):
    '''A function that defines the Discord transmission format.'''
    fields = [{"name": item.split(":", 1)[0], "value": f"`{item}`", "inline": False} for item in warn_list]
    
    embed = {
        "title": "SERVER MONITORING SYSTEM",
        "description": f"Detected **{len(warn_list)}** issue(s) requiring attention.",
        "color": 0xC0392B,
        "fields": fields,
        "footer": {
            "text": f"Reported at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    return {"embeds": [embed]}


def send_message(message):
    '''A function that sends messages to a Discord server based on a defined format.'''
    web_hook = os.getenv("DISCORD_WEBHOOK")

    if not web_hook:
        print("There is no 'DISCORD_WEBHOOK' setting in the .env file.")
        sys.exit(os.EX_NOINPUT)

    try:
        req = requests.post(web_hook, json=message, timeout=10)
        if req.status_code in (200, 204):
            log.info("Discord notification sent successfully.")
        else:
            log.error(f"Discord notification send failed  (status code: {req.status_code})")
    except requests.exceptions.RequestException as e:
        log.error(f"Discord request exception occurred: {e}")
