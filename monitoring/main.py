import logging as log
import time, signal, json
import schedule
import logger as logger

import db
from alert import (
    boot_time_check, update_boot_time,
    send_alert_batch, send_recovery_batch,
    send_heartbeat, send_weekly_summary,
)
from check import (
    server_status_check, service_status_check,
    ssl_expiry_check, disk_trend_check,
    listening_port_check, security_updates_alert_check,
)
from config import DEBOUNCE_COUNT, INTERVALS

running = True
consecutive_counts = {}


def handle_signal(signum, frame):
    global running
    log.info(f"Signal {signum} received, shutting down gracefully...")
    running = False


def check_resources():
    '''Function that runs resource checks, applies the debounce/severity logic,
    and dispatches new-problem / recovery alerts. Also handles reboot detection.'''
    global consecutive_counts

    current_items = {item["key"]: item for item in server_status_check()}
    active_issues = json.loads(db.get_state("active_issues", "{}"))

    newly_confirmed = []
    newly_resolved = []

    for key in set(consecutive_counts) | set(current_items):
        if key in current_items:
            consecutive_counts[key] = consecutive_counts.get(key, 0) + 1
            if consecutive_counts[key] >= DEBOUNCE_COUNT and key not in active_issues:
                active_issues[key] = current_items[key]
                newly_confirmed.append(current_items[key])
        else:
            if key in active_issues:
                newly_resolved.append(active_issues.pop(key))
            consecutive_counts[key] = 0

    db.set_state("active_issues", json.dumps(active_issues))

    if newly_confirmed:
        send_alert_batch(newly_confirmed)
    if newly_resolved:
        send_recovery_batch(newly_resolved)

    if boot_time_check():
        if db.get_state("last_boot") is not None:
            send_alert_batch([{
                "key": "SERVER_REBOOT",
                "message": "SERVER: Reboot detected.",
                "severity": "warning",
            }])
        update_boot_time()


def check_services():
    '''Function that runs the service check. Service events are self-resolving
    (restart succeeds or fails within the same run), so they bypass the debounce
    system and are reported immediately.'''
    items = service_status_check()
    if items:
        send_alert_batch(items)


def check_ssl():
    items = ssl_expiry_check()
    if items:
        send_alert_batch(items)


def check_ports():
    '''Function that checks expected listening ports. No debounce - a closed
    port is immediately actionable, unlike a resource spike.'''
    items = listening_port_check()
    if items:
        send_alert_batch(items)


def check_security_updates():
    items = security_updates_alert_check()
    if items:
        send_alert_batch(items)


def check_disk_trend():
    items = disk_trend_check()
    if items:
        send_alert_batch(items)


def weekly_summary():
    send_weekly_summary()


def heartbeat():
    send_heartbeat()


def main_loop():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    db.init_db()

    schedule.every(INTERVALS["resource"]).seconds.do(check_resources)
    schedule.every(INTERVALS["service"]).seconds.do(check_services)
    schedule.every(INTERVALS["port"]).seconds.do(check_ports)
    schedule.every(INTERVALS["resource"]).seconds.do(check_disk_trend)
    schedule.every(INTERVALS["ssl"]).seconds.do(check_ssl)
    schedule.every(INTERVALS["security"]).seconds.do(check_security_updates)
    schedule.every(INTERVALS["summary"]).seconds.do(weekly_summary)
    schedule.every(60).seconds.do(heartbeat)

    log.info("Server monitoring daemon started.")

    while running:
        schedule.run_pending()
        time.sleep(1)

    log.info("Server monitoring daemon stopped.")


if __name__ == "__main__":
    main_loop()
