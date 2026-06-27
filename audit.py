import os, time, re, urllib.request, json, sys
from datetime import datetime
import subprocess as sub

WEBHOOK =

FILE_KEY = 

EXEC_KEY = 

AUDIT_LOG_PATH = "/var/log/audit/audit.log"


def setup_audit_rules():
    # Delete All Existing Audit Rules.
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)

    try:
        # Add a rule to monitor sensitive files.
        sub.run(["auditctl", "-w", "/etc/passwd", "-p", "wv", "-k", FILE_KEY], check=True)
        # Add a rule to monitor command execution (execve system call).
        sub.run(["auditctl", "-a", "always,exit", "-F", "arch=b64", "-S", "execve", "-k", EXEC_KEY], check=True)
    except sub.CalledProcessError as e:
        print(f"Failed to register the audit rule. Check if you have root privileges: {e}")
        sys.exit(os.EX_NOPERM)


def cleanup_audit_rules():
    print("Delete All Existing Audit Rules.")
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)
    print("Rule removal complete. Script terminated.")


def verifying_inode_changes(last_inode):
    try:
        current_inode = os.stat(AUDIT_LOG_PATH).st_ino
        return last_inode != current_inode
    except FileNotFoundError:
        return False


def file_tailing():
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


def start():
    setup_audit_rules()

    try:
        print(f"Monitoring the {AUDIT_LOG_PATH} file...")

        for line in file_tailing():
            pass
    except KeyboardInterrupt as e:
        print(f"The script is terminated by the user: {e}")
    finally:
        cleanup_audit_rules()


if __name__ == "__main__":
    start()
