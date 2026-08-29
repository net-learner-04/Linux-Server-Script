import os

# List of Thresholds (WARNING / CRITICAL)
THRESHOLDS = {
    "cpu":              {"warning": 85.0, "critical": 95.0},
    "memory":           {"warning": 80.0, "critical": 90.0},
    "disk":             {"warning": 75.0, "critical": 90.0},
    "inode":            {"warning": 80.0, "critical": 90.0},
    "tx":               {"warning": 30.0, "critical": 60.0},
    "rx":               {"warning": 50.0, "critical": 100.0},
    "hdd_read":         {"warning": 60.0, "critical": 100.0},
    "hdd_write":        {"warning": 40.0, "critical": 80.0},
    "ssd_read":         {"warning": 200.0, "critical": 400.0},
    "ssd_write":        {"warning": 150.0, "critical": 300.0},
    "zombie":           {"warning": 10, "critical": 30},
    "file_descriptor":  {"warning": 80.0, "critical": 90.0},
    "swap":             {"warning": 50.0, "critical": 80.0},
    "temp":             {"warning": 80.0, "critical": 90.0},
}

# Adjust according to your server environment.
SERVICES = ["sshd", "tailscaled", "fail2ban", "firewalld"]

# Domains to check SSL certificate expiry for
SSL_DOMAINS = []
SSL_EXPIRY_WARNING_DAYS = 14

# Number of top processes to attach when a CPU/memory alert fires
TOP_PROCESS_COUNT = 5

# Number of consecutive over-threshold checks required before alerting
DEBOUNCE_COUNT = 3

# Disk usage trend prediction
DISK_TREND_WINDOW_DAYS = 7
DISK_TREND_ALERT_DAYS = 7

# Scheduling intervals (seconds)
INTERVALS = {
    "resource": 60,
    "service": 60,
    "port": 60,
    "ssl": 86400,       # once a day
    "security": 86400,
    "summary": 604800,  # once a week
}

_BASE = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(_BASE, "monitor.db")

# Load average threshold, expressed as a multiplier of CPU core count
LOAD_AVG_THRESHOLDS = {"warning": 1.0, "critical": 2.0}

# Ports expected to be open and listening
LISTENING_PORTS = [22, 443]

# Debian/Ubuntu (apt-based) security update count that triggers a warning
SECURITY_UPDATE_WARNING_COUNT = 10
