import json, os


def load_dev_json(filepath):
    '''Load the known devices dict from a JSON file, 
    returning an empty dict if missing or invalid.'''
    if not os.path.exists(filepath):
        print(f"The {filepath} does not exist.")
        return {}

    try:
        with open(filepath, mode="r") as file:
            return json.load(file)
    except Exception:
        return {}


def save_dev_json(devices, filepath):
    '''Save the devices dict to the given filepath as formatted JSON.'''
    with open(filepath, "w") as f:
        json.dump(devices, f, indent=2)
