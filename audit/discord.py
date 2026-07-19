import json, time, urllib.request, urllib.error
import config


def send_discord_server(webhook_url: str, message: str) -> bool:
    '''Send a message to a Discord webhook for alerting or reporting events.'''
    # Split the message into Discord-safe chunks so long reports don't trigger a 400 error.
    chunks = [message[i:i + config.DISCORD_LIMIT] for i in range(0, len(message), config.DISCORD_LIMIT)]

    success = True

    for chunk in chunks:
        json_data = {
            "content": chunk
        }

        try:
            data = json.dumps(json_data).encode("utf-8")

            req = urllib.request.Request(
                webhook_url,
                data = data,
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
        if len(chunks) > 1:
            time.sleep(1)

    return success
