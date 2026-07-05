import requests, os, random
from datetime import datetime


def discord_format(device):
    '''Build a Discord embed payload announcing a newly detected device.'''
    colors = [
        0xFFB7B2, 0xFFDAC1, 0xE2F0CB, 0xB5EAD7,
        0xC7CEEA, 0xE8AEB7, 0xB8E0D2, 0xD6E5FA
        ]

    fields = [
        {"name": "IP", "value": device["ip"], "inline": True},
        {"name": "MAC", "value": device["mac"], "inline": True}, 
        {"name": "Vendor", "value": device.get("vendor") or "Unknown Vendor", "inline": True} 
        ]
    
    embed = {
        "title": "New Device Detected",
        "color": random.choice(colors),
        "fields": fields,
        "footer": {
            "text": f"Reported at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    return {"embeds": [embed]}


def send_alert(msg):
    '''Send the given payload to the Discord webhook 
    and return whether it succeeded.'''
    try:
        webhook = os.getenv("DISCORD_WEB_HOOK")
        if not webhook:
            print("The DISCORD_WEB_HOOK environment variable has not been set.")
            return False
        request = requests.post(webhook, json=msg, timeout=10)

        if request.status_code not in (200, 204):
            return False
        return True
    except requests.exceptions.RequestException as e:
        print(f"Discord request exception occurred: {e}")
        return False
