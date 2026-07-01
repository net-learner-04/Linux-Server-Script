import os, re, csv
from datetime import datetime, timedelta
from config import LOG_DIR, KEEP_DAYS

TODAY = datetime.now().strftime("%Y-%m-%d")


def create_log_dir():
    '''If the `logs/` directory does not exist, create it.'''
    os.makedirs(LOG_DIR, exist_ok=True)


def delete_old_log():
    '''Delete old log files that exceed the 'KEEP_DAYS'(config.py) limit.'''
    file_lists = os.listdir(LOG_DIR)
    p = re.compile(r'(\d{4}-\d{2}-\d{2})\.csv$')
    
    for file in file_lists:
        m = re.search(p, file)
        if not m:
            continue

        file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        today = datetime.strptime(TODAY, "%Y-%m-%d")

        if m and (today - file_date) >= timedelta(days=KEEP_DAYS):
            os.remove(os.path.join(LOG_DIR, file))


def write_log(datas):
    '''Record the current temperature and timestamp for each device in a CSV file.'''
    # datas = all_dev_temp()
    for device, temp in datas.items():
        dev_name = device.replace(" ", "_").replace("/dev/", "")
        log_file_name = os.path.join(LOG_DIR, f"{dev_name}_{TODAY}.csv")

        file_exists = os.path.exists(log_file_name)

        with open(log_file_name, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["timestamp", "temperature"])

            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": temp
            })


def read_log(dev_name):
    '''Reads the log files for a specific device from that day 
    and returns a list of timestamps and temperatures.'''
    log_file_name = os.path.join(LOG_DIR, f"{dev_name}_{TODAY}.csv")

    with open(log_file_name, mode="r") as file:
        reader = csv.DictReader(file)
        return [(row["timestamp"], float(row["temperature"])) for row in reader]
