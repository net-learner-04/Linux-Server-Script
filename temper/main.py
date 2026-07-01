import time, sys, os
from rich.console import Console
from rich.live import Live
from collectors import all_dev_temp
from logger import create_log_dir, delete_old_log, write_log
from display import render
from config import INTERVAL


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        print("Run as root.")
        sys.exit(os.EX_NOPERM)


def start():
    '''After initialization, periodically update 
    the real-time temperature table using 'Rich Live'.'''
    root_check()

    create_log_dir()
    delete_old_log()

    print("Device temperature measurement has started.")

    console = Console()

    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                all_temps = all_dev_temp()
                write_log(all_temps)
                live.update(render(all_temps))
                time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Monitoring stopped.")


if __name__ == "__main__":
    start()