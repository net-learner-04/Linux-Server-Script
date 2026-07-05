from datetime import datetime
import copy


def find_new_dev(scanned, known):
    '''Return the list of scanned devices whose MAC address 
    is not present in the known devices dict.'''
    not_exists_dev = []

    for dev in scanned:
        if dev["mac"] not in known:
            not_exists_dev.append(dev)
        
    return not_exists_dev


def update_known_dev(scanned, known):
    '''Return an updated copy of known devices, adding new entries 
    and refreshing last_seen timestamps.'''
    updated = copy.deepcopy(known)
    now = datetime.now().isoformat()

    for dev in scanned:
        if dev["mac"] not in known:
            updated[dev["mac"]] = {
                "vendor": None,
                "first_seen": now,
                "last_seen": now
            }
        else:
            updated[dev["mac"]]["last_seen"] = now
    
    return updated
