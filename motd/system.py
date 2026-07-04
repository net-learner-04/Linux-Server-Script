import psutil, subprocess as sub


def time_calculate(sec):
    total_sec = int(float(sec))

    days, remainder = divmod(total_sec, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{days} days {hours} hours {minutes} minutes {seconds} seconds"


def get_uptime():
    try:
        with open("/proc/uptime", mode="r") as file:
            contents = file.read().split()

        uptime = time_calculate(contents[0])
        idle_time = time_calculate(contents[1])

        return uptime, idle_time
    except FileNotFoundError as e:
        print(f"The file cannot be found. Please check the path: {e}")
        return "", ""


def get_dev_info():
    cpu_usage = psutil.cpu_percent(interval=None)
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent

    return cpu_usage, memory_usage, disk_usage


def get_update_number():
    try:
        result = sub.run(
            ["dnf", "check-update", "-q"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode not in (0, 100):
            print(f"dnf check-update failed with code {result.returncode}")
            return ""

        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        update_count = len(lines)

        if update_count == 0:
            return "Update: up to date"
        return f"Update: {update_count} pending"

    except sub.TimeoutExpired:
        print("dnf check-update timed out")
        return ""
    except Exception as e:
        print(f"Command-Line Argument Error: {e}")
        return ""


def get_last_login():
    try:
        result = sub.run(
            ["last", "-2", "--time-format", "iso"],
            capture_output=True, text=True, timeout=3
        )
        lines = result.stdout.strip().split("\n")

        for line in lines:
            parts = line.split()
            if not line or "wtmp begins" in line or len(parts) < 4:
                continue

            user = parts[0]
            ip = "localhost" if user == "reboot" else parts[2]
            date_part, time_part = parts[3].split("T")
            login_time = time_part.split("+")[0].split("-")[0]

            return f"Last login: {date_part} {login_time} ({user}: {ip})"

        return ""
    except Exception as e:
        print(f"Command-Line Argument Error: {e}")
        return ""
