import subprocess as sub
import os, pathlib, psutil, math, sys

def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        print("Run as root")
        sys.exit(1)

def kb_to_gb(kb):
    '''Function to convert kilobytes to gigabytes'''
    return math.ceil(kb / (1024 ** 2))

def swap_status():
    '''Function to check the current status of the swap file'''
    result = sub.run(["swapon", "-s"],
                      capture_output=True,
                        text=True).stdout
    lines = [line for line in result.splitlines() if line.strip()]
    return len(lines) > 1

def check_swap_total_memory(swap_memory):
    '''A function that calculates the total size of each active swap file
      to determine whether to delete the existing one'''
    memory_list = []

    result = sub.run(["swapon", "-s"],
                      capture_output=True,
                        text=True).stdout
    lines = [line for line in result.splitlines() if line.strip()]

    for line in lines[1:]:
        col = line.split()
        memory_list.append(int(col[2]))
    
    total_swap_kb = sum(memory_list)
    total_swap_gb = kb_to_gb(total_swap_kb)

    if total_swap_gb < swap_memory:
        return True
    else:
        return False

def swap_create(memory_size):
    '''A function to create a swap file, set permissions, and mount it'''
    swap_file_list = []

    file_path = pathlib.Path("/swapfile")

    result = sub.run(["swapon", "-s"],
                      capture_output=True,
                        text=True).stdout
    lines = [line for line in result.splitlines() if line.strip()]

    for line in lines[1:]:
        col = line.split()
        swap_file_list.append(col[0])

    for file in swap_file_list:
        if file == str(file_path):
            sub.run(["swapoff", "-v", "/swapfile"])

    swap_file = sub.run(["dd", 
                         "if=/dev/zero",
                           f"of={file_path}",
                             "bs=1024",
                               f"count={memory_size * 1024 * 1024}"])
    if swap_file.returncode != 0:
        print("A new swap file was not created.")
        sys.exit(1)
    
    sub.run(["chmod", "600", str(file_path)], check=True)
    sub.run(["mkswap", str(file_path)], check=True)
    sub.run(["swapon", str(file_path)], check=True)
    
    if not swap_status():
        print(f"The swap file {file_path} could not be created properly.")
        sys.exit(1)
    
    fstab = pathlib.Path("/etc/fstab")
    fstab_content = fstab.read_text()
    if not any(line.startswith("/swapfile ") for line in fstab_content.splitlines()):
        with open(fstab, mode="a") as f:
            f.write("\n/swapfile swap swap defaults 0 0\n")
    print(f"Swap file created and registered {str(fstab)} successfully.")

def memory_calculate():
    '''A function that calculates the amount of physical memory installed on the device
      and determines the recommended swap space'''
    memory = psutil.virtual_memory()
    memory_kb = memory.total / 1024
    memory_gb = kb_to_gb(memory_kb)
    
    if memory_gb < 4:
        return 2
    elif memory_gb < 16:
        return 4
    elif memory_gb < 64:
        return 8
    elif memory_gb < 256:
        return 16
    else:
        return 32

def start():
    root_check()
    SWAP_MEMORY_VALUE = memory_calculate()
    if check_swap_total_memory(SWAP_MEMORY_VALUE):
        print("Starting creation due to insufficient swap space")
        swap_create(SWAP_MEMORY_VALUE)
    else:
        print("The script has terminated because there is already sufficient swap space available on the system.")

if __name__ == "__main__": 
    start()
