from hardware import detect_power_method
from logger import create_daily_log_file, write_log
from parser import (
    parse_logs,
    calculate_cost,
    is_last_day_of_month,
)
from discord import send_to_discord


def start():
    method = detect_power_method()

    log_path = create_daily_log_file()
    write_log(log_path, method)

    if is_last_day_of_month():
        total_uptime, total_wh = parse_logs()
        total_kwh, cost = calculate_cost(total_wh)
        send_to_discord(total_uptime, total_kwh, cost)


if __name__ == "__main__":
    print("Start Power Calculation...")
    start()
