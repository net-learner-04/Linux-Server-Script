import os, time, re, urllib.request, json, sys, time
from datetime import datetime
import subprocess as sub


# Discord web hook.
WEBHOOK = 

FILE_KEY = "my_secret_key"
EXEC_KEY = "my_exec_key"

AUDIT_LOG_PATH = "/var/log/audit/audit.log"

MESSAGE_QUEUE = []
LAST_SENT = 0
# sec
INTERVAL = 10

# Discord's hard limit is 2000 chars per message; keep some margin.
DISCORD_LIMIT = 1900

# Keywords used to filter EXECVE command lines that are actually worth reporting.
# Matched against the binary/interpreter name (no options) so variants like
# python3, python3.11, /usr/bin/python are all caught by "python".
# Short tokens (nc, su, sh, dd, etc.) are matched with word boundaries in
# is_suspicious() to avoid false positives like "sync", "bash", "disk".
KEYWORDS = [
    "wget", "curl",
    "nc", "ncat", "netcat",
    "chmod",
    "base64",
    "/etc/shadow", "/etc/sudoers",
    "rm",
    "sudo", "su",
    "python", "python3", "perl", "ruby",
    "bash", "sh", "zsh", "dash",
    "history",
    "iptables", "nft",
    "crontab",
    "ssh-keygen", "authorized_keys",
    "dd",
    "nohup", "disown",
]

# Pre-compile a single regex with word boundaries for accurate matching.
_KEYWORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b",
    re.IGNORECASE
)


def is_suspicious(cmd_line: str) -> bool:
    '''Check whether a command line contains any keyword worth reporting.'''
    return bool(_KEYWORD_PATTERN.search(cmd_line))


def setup_audit_rules():
    '''Set up audit rules to monitor sensitive file access and process execution using auditctl. 
    Requires root privileges.'''
    # Delete All Existing Audit Rules.
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)

    try:
        # Add a rule to monitor sensitive files.
        sub.run(["auditctl", "-w", "/etc/passwd", "-p", "wa", "-k", FILE_KEY], check=True)
        # Add a rule to monitor command execution (execve system call).
        sub.run(["auditctl", "-a", "always,exit", "-F", "arch=b64", "-S", "execve", "-k", EXEC_KEY], check=True)
    except sub.CalledProcessError as e:
        print(f"Failed to register the audit rule. Check if you have root privileges: {e}")
        sys.exit(os.EX_NOPERM)


def cleanup_audit_rules():
    '''Remove all audit rules and reset audit configuration on script exit.'''
    print("Delete All Existing Audit Rules.")
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)
    print("Rule removal complete. Script terminated.")


def verifying_inode_changes(last_inode):
    '''Check if the audit log file has been rotated or replaced by comparing inode values.'''
    try:
        current_inode = os.stat(AUDIT_LOG_PATH).st_ino
        return last_inode != current_inode
    except FileNotFoundError:
        return False


def file_tailing():
    '''Continuously read new lines from the audit log file and handle log rotation.'''
    current_inode = None
    file = None

    try:
        file = open(AUDIT_LOG_PATH, mode="r")
        file.seek(0, 2)
        current_inode = os.stat(AUDIT_LOG_PATH).st_ino

        while True:
                line = file.readline()
                if line == "":
                    time.sleep(0.5)
                    if verifying_inode_changes(current_inode):
                        file.close()

                        print("The log file has been replaced. Reopen the new file.")
                        file = open(AUDIT_LOG_PATH, mode="r")
                        current_inode = os.stat(AUDIT_LOG_PATH).st_ino
                    continue
                yield line

    except Exception as e:
        print(f"An error occurred during tailing: {e}")
    finally:
        if file:
            file.close()    


def parse_audit_log(line):
    '''Parse a raw audit log line into a dictionary of key-value pairs.'''
    p = r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|([^"\s]+))'
    m = re.findall(p, line)

    data = dict()
    
    for item in m:
        key = item[0]
        value = item[1] if item[1] else item[2]
        data[key] = value
    
    return data


def flush(force=False):
    '''Send queued messages to Discord while respecting rate limiting.'''
    global LAST_SENT

    if not MESSAGE_QUEUE:
        return

    now = time.time()

    if not force and now - LAST_SENT < INTERVAL:
        return

    msg = "\n".join(MESSAGE_QUEUE)
    MESSAGE_QUEUE.clear()

    send_discord_server(msg)
    LAST_SENT = now


def send_discord_server(message):
    '''Send a message to a Discord webhook for alerting or reporting events.'''
    # Split the message into Discord-safe chunks so long reports don't trigger a 400 error.
    chunks = [message[i:i + DISCORD_LIMIT] for i in range(0, len(message), DISCORD_LIMIT)]

    success = True

    for chunk in chunks:
        json_data = {
            "content": chunk
        }

        try:
            data = json.dumps(json_data).encode("utf-8")

            req = urllib.request.Request(
                WEBHOOK,
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


def start():
    '''Main loop that monitors audit logs, processes events, and sends alerts/reports.'''
    buffer = dict()
    reports = []
    setup_audit_rules()

    start_time = datetime.now()

    try:
        print(f"Monitoring the {AUDIT_LOG_PATH} file...")

        for line in file_tailing():
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

                    send_discord_server(alert_msg)

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
