import subprocess as sub
import logging as log
import datetime as dt
import psutil, requests, os, dotenv


dotenv.load_dotenv()

NOWDATE = dt.datetime.now().strftime("%Y-%m-%d")
THRESHOLD = 1.0
SERVICES = ["nginx", "sshd", "httpd"]

log.basicConfig(
    filename=f"{NOWDATE}_server.log",
    level=log.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def sever_status_check():
    '''Use `psutil` to check CPU, memory, and disk usage 
    and determine whether they exceed a threshold (e.g., 85%)'''
    warn_list = []

    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent

    if cpu_usage > THRESHOLD:
        warn_list.append(f"CPU_USAGE: {cpu_usage}")
    if memory_usage > THRESHOLD:
        warn_list.append(f"MEMORY_USAGE: {memory_usage}")
    if disk_usage > THRESHOLD:
        warn_list.append(f"DISK_USAGE: {disk_usage}")
    
    return warn_list


def service_status_check():
    '''Function to check the status of essential services (httpd, nginx, sshd, etc.).'''
    warn_list = []

    for service in SERVICES:
        if sub.run(["systemctl", "is-active", service], stdout=None, stderr=None).returncode != 0:
            log.warning(f"The {service} is currently disabled. Attempting to restart...")
            if sub.run(["systemctl", "restart", service]).returncode == 0:
                log.info(f"The {service} restart success.")
                warn_list.append(f"Detected that the {service} service is down -> Automatic restart successful.")
            else:
                log.error(f"The {service} restart failed.")
                warn_list.append(f"Detected that the {service} service is down -> Automatic restart failed.")

    return warn_list


def discord_format(warn_list):
    '''A function that defines the Discord transmission format.'''
    data = "\n".join(warn_list)
    message = {
        "content": data
    }

    return message


def send_message(message):
    '''A function that sends messages to a Discord server based on a defined format.'''
    web_hook = os.getenv("DISCORD_WEBHOOK")

    if not web_hook:
        print("There is no 'DISCORD_WEBHOOK' setting in the .env file.")
        return

    req = requests.post(web_hook, json=message)
    if req.status_code == 200 or req.status_code == 204:
        print("Discord notification sent successfully.")
    else:
        print(f"Discord notification send failed  (status code: {req.status_code})")


def start():
    system_warn_list = sever_status_check()
    service_warn_list = service_status_check()
    errors = system_warn_list + service_warn_list
    if len(errors) > 0:
        format_message = discord_format(errors)
        send_message(format_message)


if __name__ == "__main__":
    start()