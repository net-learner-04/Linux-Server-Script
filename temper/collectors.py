import subprocess as sub
import psutil, glob, re, json


def cpu_temp():
    '''Use 'psutil' to collect CPU core and 
    package temperatures and return them as a dictionary.'''
    datas = psutil.sensors_temperatures()
    return_datas = dict()

    for data in datas.get("coretemp", []):
        return_datas[data.label] = data.current

    return return_datas


def ssd_temp():
    '''Collect NVMe device temperatures using 'smartctl' 
    and return them as a dictionary.'''
    dev_files = glob.glob("/dev/nvme*")
    p = re.compile('/dev/nvme\d+$')
    return_datas = dict()

    for dev in sorted(dev_files):
        m = re.match(p, dev)
        if not m:
            continue

        try:
            json_data = sub.run(["smartctl", "-A", "--json", m.group()]
                                , capture_output=True
                                , text=True)
            
            if json_data.returncode == 0:
                result = json.loads(json_data.stdout)
                # NVMe method.
                if "nvme_smart_health_information_log" in result:
                    temp = result["nvme_smart_health_information_log"]["temperature"]
                    return_datas[result["device"]["name"]] = temp
                # SATA method.
                elif "ata_smart_attributes" in result:
                    attributes = result["ata_smart_attributes"]["table"]
                    for attribute in attributes:
                        if attribute.get("name") in ["Temperature_Celsius", "Airflow_Temperature_Cel"]:
                            temp = attribute["raw"]["value"]
                            return_datas[result["device"]["name"]] = temp
        except FileNotFoundError:
            print("The smartctl package is not installed.")
        except PermissionError as e:
            print(f"You do not have permission: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failure: {e}")
    
    return return_datas


def all_dev_temp():
    '''Combines the results of `cpu_temp()` 
    and `ssd_temp()` into a single dictionary and returns it.'''
    result = {}
    result.update(cpu_temp())
    result.update(ssd_temp())
    return result