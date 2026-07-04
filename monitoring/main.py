import logging as log
import os

import logger_setup
from utils import root_check
from boot import boot_time_check, update_boot_time
from alert import last_alert_check, update_last_alert, discord_format, send_message
from checks.system_checks import server_status_check
from checks.service_checks import service_status_check

from config import BOOTFILE


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
    log.info("Start the system monitoring process.")
    start()
