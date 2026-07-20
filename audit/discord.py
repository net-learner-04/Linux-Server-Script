import json, time, urllib.request, urllib.error
from datetime import datetime, timezone
import config

DISCORD_EMBED_DESC_LIMIT = 4096
DISCORD_EMBED_COLOR = {
    "info": 0x3498DB,
    "success": 0x2ECC71,
    "warning": 0xF1C40F,
    "error": 0xE74C3C,
}


def send_discord_server(
    webhook_url: str,
    message: str,
    title: str = "Notification",
    level: str = "info",
) -> bool:
    '''Send a message to a Discord webhook for alerting or reporting events, using embeds.'''
    # Split the message into Discord-safe chunks so long reports don't trigger a 400 error.
    limit = getattr(config, "DISCORD_EMBED_LIMIT", DISCORD_EMBED_DESC_LIMIT)
    chunks = [message[i:i + limit] for i in range(0, len(message), limit)] or [""]
    color = DISCORD_EMBED_COLOR.get(level, DISCORD_EMBED_COLOR["info"])
    total = len(chunks)
    success = True

    for idx, chunk in enumerate(chunks, start=1):
        embed = {
            "title": title if total == 1 else f"{title} ({idx}/{total})",
            "description": f"```{chunk}```",  # wrap in code block for log readability
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        json_data = {"embeds": [embed]}

        try:
            data = json.dumps(json_data).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as response:
                if response.status != 204:
                    print(f"Discord transmission response status error: {response.status}")
                    success = False
        except urllib.error.HTTPError as e:
            print(f"Failed to send Discord notification: {e.code}: {e.read().decode()}")
            success = False
        # Small delay between chunks to avoid hitting Discord's rate limit.
        if total > 1:
            time.sleep(1)

    return success
