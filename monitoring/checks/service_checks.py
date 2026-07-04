import subprocess as sub
import logging as log

from config import SERVICES


def service_status_check():
    '''Function to check the status of essential services (httpd, nginx, sshd, etc.).'''
    warn_list = []

    for service in SERVICES:
        # sub.DEVNULL : Hide Terminal std Output
        if sub.run(["systemctl", "is-active", service], stdout=sub.DEVNULL, stderr=sub.DEVNULL).returncode != 0:
            log.warning(f"The {service} is currently disabled. Attempting to restart...")
            if sub.run(["systemctl", "restart", service], stdout=sub.DEVNULL, stderr=sub.DEVNULL).returncode == 0:
                log.info(f"The {service} restart success.")
                warn_list.append(f"SERVICE: {service} -> Automatic restart successful.")
            else:
                log.error(f"The {service} restart failed.")
                warn_list.append(f"SERVICE: {service} -> Automatic restart failed.")

    return warn_list