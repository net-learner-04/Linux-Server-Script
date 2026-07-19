import os, time
from datetime import datetime
from dotenv import load_dotenv
# Import modular components
import config
from audit import setup_audit_rules, cleanup_audit_rules
from tailer import file_tailing
from parser import parse_audit_log, is_suspicious
from discord import send_discord_server


# Run in the background using tmux.

# Load environment variables
load_dotenv()

WEBHOOK = os.getenv("WEBHOOK")
FILE_KEY = os.getenv("FILE_KEY", "my_secret_key")
EXEC_KEY = os.getenv("EXEC_KEY", "my_exec_key")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "/var/log/audit/audit.log")

MESSAGE_QUEUE = []
LAST_SENT = 0


def flush(force=False):
    '''Send queued messages to Discord while respecting rate limiting.'''
    global LAST_SENT

    if not MESSAGE_QUEUE:
        return

    now = time.time()

    if not force and now - LAST_SENT < config.INTERVAL:
        return

    msg = "\n".join(MESSAGE_QUEUE)
    MESSAGE_QUEUE.clear()

    send_discord_server(WEBHOOK, msg)
    LAST_SENT = now


def start():
    '''Main loop that monitors audit logs, processes events, and sends alerts/reports.'''
    buffer = dict()
    reports = []
    setup_audit_rules(FILE_KEY, EXEC_KEY)

    start_time = datetime.now()

    try:
        print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"Monitoring the {AUDIT_LOG_PATH} file...")

        for line in file_tailing(AUDIT_LOG_PATH):
            parsed_data = parse_audit_log(line)

            if "type" not in parsed_data:
                continue
            
            log_type = parsed_data.get("type")
            log_key = parsed_data.get("key")
            msg_id = parsed_data.get("msg_id")

            if log_type == "SYSCALL":
                if parsed_data.get("key") == FILE_KEY:
                    exe_path = parsed_data.get("exe", "Unknown")
                    uid_val = parsed_data.get("uid", "Unknown")

                    alert_msg = (
                        f"    ALERT Sensitive file access detected\n"
                        f"    Target: /etc/passwd\n"
                        f"    Program: {exe_path}\n"
                        f"    UID: {uid_val}\n"
                        f"    Event ID: {msg_id}"
                    )

                    send_discord_server(WEBHOOK, alert_msg)

                elif log_key == EXEC_KEY:
                    buffer[msg_id] = {
                        "exe": parsed_data.get("exe", "Unknown"),
                        "uid": parsed_data.get("uid", "Unknown"),
                        # A list to store the commands used when the type is EXECVE.
                        "args": []
                    }
            elif log_type == "EXECVE":
                if msg_id in buffer:
                    for key in sorted(parsed_data.keys()):
                        if key.startswith("a") and key[1:].isdigit():
                            # parsed_data[key] is already decoded (see parse_audit_log).
                            buffer[msg_id]["args"].append(parsed_data[key])

                    if len(buffer) > 10000:
                        buffer.clear()

                    cmd_line = " ".join(buffer[msg_id]["args"])

                    # Only keep command lines that match a known suspicious keyword,
                    # so reports stay short and relevant instead of hitting Discord's length limit.
                    if is_suspicious(cmd_line):
                        exe = buffer[msg_id]["exe"]
                        uid = buffer[msg_id]["uid"]
                        reports.append(f"[{exe} / uid={uid}] {cmd_line}")

                    buffer.pop(msg_id)
            current_time = datetime.now()
            elapsed = (current_time - start_time).total_seconds()

            # Command monitoring time (in seconds)
            if elapsed >= 300:
                if reports:
                    report_msg = f"EXEC Report\n" + "\n".join(reports)
                    MESSAGE_QUEUE.append(report_msg)
                    flush()
                
                reports = []
                start_time = current_time
    except KeyboardInterrupt as e:
        print(f"The script is terminated by the user: {e}")
    finally:
        cleanup_audit_rules()


if __name__ == "__main__":
    start()
