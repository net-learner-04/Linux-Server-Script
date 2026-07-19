import csv, calendar
from datetime import datetime, date
import config

def parse_logs():
    """Aggregate this month's logs into total uptime (s) and total energy consumption (Wh)."""
    csv_files = config.DIR_PATH.glob("*.csv")
    total_uptime = 0.0
    total_wh = 0.0
    today = date.today()

    for file_path in csv_files:
        try:
            file_date_obj = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

        if file_date_obj.year != today.year or file_date_obj.month != today.month:
            continue

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Header Skip
            next(reader)

            rows = list(reader)
            if not rows:
                continue

            day_uptimes = [float(row[1]) for row in rows]
            total_uptime += max(day_uptimes)

            prev_ts = None
            for row in rows:
                ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                power = row[2]

                if prev_ts is not None and power != "":
                    hours = (ts - prev_ts).total_seconds() / 3600
                    total_wh += float(power) * hours

                prev_ts = ts

    return total_uptime, total_wh


def is_last_day_of_month():
    """Return True if today is the last calendar day of the current month."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    return today.day == last_day
