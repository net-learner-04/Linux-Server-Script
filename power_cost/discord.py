import requests
from datetime import datetime, date
import config

def send_to_discord(total_uptime, total_kwh, cost):
    """Send a monthly usage/cost summary message to the configured Discord webhook."""
    month = date.today().month

    embed = {
        "title": f"{month} Month Electricity Usage Report",
        "color": 0xF1C40F,
        "fields": [
            {
                "name": "Total Uptime",
                "value": f"{total_uptime / 3600:.2f} hours",
                "inline": True
            },
            {
                "name": "Estimated Electricity Consumption",
                "value": f"{total_kwh:.3f} kWh",
                "inline": True
            },
            {
                "name": "Estimated Electricity Bill",
                "value": f"{cost:,.0f} KRW",
                "inline": True
            }
        ],
        "footer": {
            "text": "Power Cost Monitor"
        },
        "timestamp": datetime.now().isoformat()
    }

    payload = {"embeds": [embed]}

    try:
        response = requests.post(config.WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Discord Transfer Failed: {e}")
