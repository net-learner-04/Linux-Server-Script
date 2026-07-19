import sys, os
import subprocess as sub

def setup_audit_rules(file_key: str, exec_key: str):
    '''Set up audit rules to monitor sensitive file access and process execution using auditctl. 
    Requires root privileges.'''
    # Delete All Existing Audit Rules.
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)

    try:
        # Add a rule to monitor sensitive files.
        sub.run(["auditctl", "-w", "/etc/passwd", "-p", "wa", "-k", file_key], check=True)
        # Add a rule to monitor command execution (execve system call).
        sub.run(["auditctl", "-a", "always,exit", "-F", "arch=b64", "-S", "execve", "-k", exec_key], check=True)
    except sub.CalledProcessError as e:
        print(f"Failed to register the audit rule. Check if you have root privileges: {e}")
        sys.exit(os.EX_NOPERM)


def cleanup_audit_rules():
    '''Remove all audit rules and reset audit configuration on script exit.'''
    print("Delete All Existing Audit Rules.")
    sub.run(["auditctl", "-D"], stdout=sub.DEVNULL, stderr=sub.DEVNULL)
    print("Rule removal complete. Script terminated.")
