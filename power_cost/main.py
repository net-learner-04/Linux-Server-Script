import power
import logger
import parser
import discord

def start():
    method = power.detect_power_method()
    log_path = logger.create_daily_log_file()
    logger.write_log(log_path, method)

    if parser.is_last_day_of_month():
        total_uptime, total_wh = parser.parse_logs()
        total_kwh, cost = power.calculate_cost(total_wh)
        discord.send_to_discord(total_uptime, total_kwh, cost)


if __name__ == "__main__":
    print("Start Power Calculation...")
    start()
