import logging as log
import os, sys
import logger as logger
from alert import boot_time_check, update_boot_time
from alert import last_alert_check, update_last_alert, discord_format, send_message
from checks import server_status_check, service_status_check
from config import BOOTFILE


# def root_check():
#     '''A function to check if the program is running with root privileges'''
#     if os.geteuid() != 0:
#         log.critical("Root privilege required to run this script.")
#         print("Run as root.")
#         sys.exit(os.EX_NOPERM)


def start():
    root_check()
    system_warn_list = server_status_check()
    service_warn_list = service_status_check()
    errors = system_warn_list + service_warn_list

    if boot_time_check():
        if os.path.exists(BOOTFILE):
            errors.append("SERVER: Reboot detected.")
        update_boot_time()

    if len(errors) > 0:
        if last_alert_check():
            format_message = discord_format(errors)
            send_message(format_message)
            update_last_alert()


if __name__ == "__main__":
    start()
