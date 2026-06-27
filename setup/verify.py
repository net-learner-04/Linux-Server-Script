import subprocess as sub
import socket, sys


SERVICES = ["sshd", "firewalld", "fail2ban"]

NOT_ACTIVE_SERVICES = []


def service_status_check():
    '''A function that checks whether the sshd and 
    firewall-related services that were installed are running properly.'''
    for service in SERVICES:
        result = sub.run(["systemctl", "is-active", service],
                         capture_output=True,
                         text=True)
        
        if result.stdout.strip() == "active":
            print(f"{service} is active.")
        else:
            NOT_ACTIVE_SERVICES.append(service)


def ssh_port_check():
    '''A function to verify whether the SSH port number, 
    which was changed manually, has been applied correctly.'''
    port = int(sys.argv[1])

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        result = sock.connect_ex(("127.0.0.1", port))
    
    if result == 0:
        print("SSH service is listening.")
    else:
        print("SSH service is NOT listening.")


def config_file_check():
    '''A function that verifies whether the SSH account security script 
    configured in the 'sshd_config' file is functioning properly.'''
    permit_root = False
    password_auth = False

    with open("/etc/ssh/sshd_config", mode="r") as file:
        for line in file.splitlines():
            if line.split() == ["PermitRootLogin", "no"]:
                permit_root = True
            if line.split() == ["PasswordAuthentication", "no"]:
                password_auth = True

    print("PermitRootLogin no" if permit_root else "PermitRootLogin no is NOT applied.")
    print("PasswordAuthentication no" if password_auth else "PasswordAuthentication no is NOT applied.")


def user_check():
    '''A function to verify whether a created user actually exists.'''
    username = sys.argv[2]

    with open("/etc/passwd") as file:
        for line in file:
            if line.startswith(username + ":"):
                print("The user has been successfully created.")
                return

    print("User not found.")


def start():
    service_status_check()
    ssh_port_check()
    config_file_check()
    user_check()
    
    if len(NOT_ACTIVE_SERVICES) > 0:
        for service in NOT_ACTIVE_SERVICES:
            print(f"{service} is NOT active.")


if __name__ == "__main__":
    start()
    print("Script completed successfully.")
