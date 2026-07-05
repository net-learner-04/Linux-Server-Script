import os, sys, asyncio, dotenv
import scan, identify, storage, compare, discord
from pathlib import Path


dotenv.load_dotenv(Path(__file__).parent / ".env")

SUBNET = os.getenv("SUBNET")
DEVICES_FILE = os.getenv("DEVICES_FILE")
SERVER_MAC = os.getenv("SERVER_MAC")
LOCK_FILE = os.getenv("LOCK_FILE")


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        print("Run as root.")
        sys.exit(os.EX_NOPERM)


def acquire_lock():
    '''Create a lock file to prevent multiple instances 
    from running simultaneously.'''
    if os.path.exists(LOCK_FILE):
        print("Another instance is already running. Exiting.")
        sys.exit(1)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def release_lock():
    '''Remove the lock file to release the running instance lock.'''
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


async def main():
    '''Scan the network for devices, detect new ones, 
    alert via Discord, and persist the updated device list.'''
    if not SUBNET or not DEVICES_FILE or not SERVER_MAC or not LOCK_FILE:
        print("Required environment variables have not been set. " \
              "Please check the .env file.")
        sys.exit(os.EX_NOINPUT)

    known = storage.load_dev_json(DEVICES_FILE)
    first_run = len(known) == 0

    await identify.vendor_db()

    scanned = scan.scan_network(SUBNET)

    scanned = [dev for dev in scanned if dev["mac"] != SERVER_MAC]

    if not scanned:
        print("No devices found on the network.")
        return

    new_devices = compare.find_new_dev(scanned, known)

    if new_devices:
        vendors = await asyncio.gather(
            *[identify.get_vendor(dev["mac"]) for dev in new_devices]
        )
        for dev, vendor in zip(new_devices, vendors):
            dev["vendor"] = vendor

    updated_known = compare.update_known_dev(scanned, known)

    for dev in new_devices:
        updated_known[dev["mac"]]["vendor"] = dev.get("vendor")

    if not first_run and new_devices:
        for dev in new_devices:
            msg = discord.discord_format(dev)
            success = discord.send_alert(msg)
            if not success:
                print(f"Failed to send message for {dev['mac']}")
    elif first_run:
        print(f"First run: registered {len(scanned)} devices" \
               "without alerting.")

    storage.save_dev_json(updated_known, DEVICES_FILE)

    print(f"Scan complete. {len(new_devices)} new device(s) found.")


if __name__ == "__main__":
    root_check()
    acquire_lock()
    try:
        asyncio.run(main())
    finally:
        release_lock()
