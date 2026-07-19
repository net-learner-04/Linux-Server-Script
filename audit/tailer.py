import os, time

def verifying_inode_changes(audit_log_path: str, last_inode) -> bool:
    '''Check if the audit log file has been rotated or replaced by comparing inode values.'''
    try:
        current_inode = os.stat(audit_log_path).st_ino
        return last_inode != current_inode
    except FileNotFoundError:
        return False


def file_tailing(audit_log_path: str):
    '''Continuously read new lines from the audit log file and handle log rotation.'''
    current_inode = None
    file = None

    try:
        file = open(audit_log_path, mode="r")
        file.seek(0, 2)
        current_inode = os.stat(audit_log_path).st_ino

        while True:
            line = file.readline()
            if line == "":
                time.sleep(0.5)
                if verifying_inode_changes(audit_log_path, current_inode):
                    file.close()

                    print("The log file has been replaced. Reopen the new file.")
                    file = open(audit_log_path, mode="r")
                    current_inode = os.stat(audit_log_path).st_ino
                continue
            yield line

    except Exception as e:
        print(f"An error occurred during tailing: {e}")
    finally:
        if file:
            file.close()
