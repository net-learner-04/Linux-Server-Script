import os

# List of Thresholds 
THRESHOLDS = {
    "cpu": 85.0,
    "memory": 80.0,
    "disk": 75.0,
    "tx": 30.0,
    "rx": 50.0,
    "hdd_read": 60.0,
    "hdd_write": 40.0,
    "ssd_read": 200.0,
    "ssd_write": 150.0,
    "zombie": 10,
    "file_descriptor": 80.0,
    "swap": 50.0,
    "temp": 80.0,
}

# Adjust according to your server environment.
SERVICES = ["sshd", "tailscaled", "cloudflared"]

# minutes
COOLDOWN = 15 

_BASE = os.path.dirname(os.path.abspath(__file__))

ALERTFILE = os.path.join(_BASE, ".last_alert")

BOOTFILE  = os.path.join(_BASE, ".last_boot")
