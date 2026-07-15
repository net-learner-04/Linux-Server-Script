import os, sys, ast, time, pathlib, subprocess as sub, logging as log
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging.handlers import TimedRotatingFileHandler


# To keep the code running in the background and monitoring the directory, 
# execute the code using the command. -> nohup python(3) <file name>.py &


# Fall back process
try:
    STDLIB_MODULES = sys.stdlib_module_names
except AttributeError:
    import distutils.sysconfig as sysconfig
    import os as _os

    STDLIB_MODULES = set(sys.builtin_module_names)

    stdlib_path = sysconfig.get_python_lib(standard_lib=True)
    if _os.path.isdir(stdlib_path):
        for name in _os.listdir(stdlib_path):
            if name.endswith(".py"):
                STDLIB_MODULES.add(name[:-3])
            elif _os.path.isdir(_os.path.join(stdlib_path, name)) and not name.startswith("_"):
                STDLIB_MODULES.add(name)

    dynload_path = _os.path.join(stdlib_path, "lib-dynload")
    if _os.path.isdir(dynload_path):
        for name in _os.listdir(dynload_path):
            mod_name = name.split(".")[0]
            STDLIB_MODULES.add(mod_name)


DIRECTORY_PATH = pathlib.Path(__file__).parent

MODULES_FILE = DIRECTORY_PATH / "modules.txt"

def mkdir_log():
    os.makedirs(os.path.join(os.path.dirname(__file__), "watchdog_log"), exist_ok=True)

mkdir_log()

handler = TimedRotatingFileHandler(
    filename=os.path.join(os.path.dirname(__file__), "watchdog_log", "watchdog.log"),
    when="midnight",
    backupCount=7
)

log.basicConfig(
    handlers=[handler],
    level=log.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class Target:
    watchDir = DIRECTORY_PATH

    def __init__(self):
        self.observer = Observer()
    

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watchDir, recursive=True)

        result = scan_directory(self.watchDir)
        update_txt(result, MODULES_FILE)

        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.observer.join()


class Handler(FileSystemEventHandler):
    def on_created(self, event):
        '''A function that calls `scan_directory` → `update_modules_txt` after 
        filtering '.py' files in response to a watchdog event callback.'''
        if pathlib.Path(event.src_path).suffix == ".py":
            result = scan_directory(DIRECTORY_PATH)
            update_txt(result, MODULES_FILE)
        else:
            pass


    def on_modified(self, event):
        if pathlib.Path(event.src_path).suffix == ".py":
            result = scan_directory(DIRECTORY_PATH)
            update_txt(result, MODULES_FILE)
        else:
            pass


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.getuid() != 0:
        log.critical("Root privilege required.")
        sys.exit(os.EX_NOPERM)


def parse_import(file_path):
    '''A function that parses a single '.py' file using ast and returns a set of module names.'''
    return_module = set()

    try:
        with open(file_path, mode="r") as file:
            python_file = file.read()
            modules = ast.parse(python_file)
            imports = [value for value in ast.walk(modules) if isinstance(value, (ast.Import, ast.ImportFrom))]

        for module in imports:
            if isinstance(module, ast.Import):
                for alias in module.names:
                    top_level = alias.name.split(".")[0]
                    if top_level not in STDLIB_MODULES:
                        return_module.add(top_level)
            elif isinstance(module, ast.ImportFrom):
                if module.module is None:
                    continue
                if module.level and module.level > 0:
                    continue
                top_level = module.module.split(".")[0]
                if top_level not in STDLIB_MODULES:
                    return_module.add(top_level)
    except SyntaxError:
        log.warning(f"Skipping {file_path} due to syntax error.")

    return return_module


def scan_directory(dir_path):
    '''A function that collects all ‘.py’ files in a directory and 
    then calls ‘parse_imports’ to sum up the module names.'''
    files = pathlib.Path(dir_path).rglob("*.py")
    result = set()

    for file in files:
        if file.name == pathlib.Path(__file__).name:
            continue
        result.update(parse_import(file))
    
    return result


def pip_install(modules):
    '''A function that installs the modules specified in the list passed as parameters.'''
    for module in modules:
        try:
            sub.run(["pip3", "install", module, "--quiet"], check=True)
            log.info(f"{module} installed successfully.")
        except sub.CalledProcessError as e:
            log.error(f"{module} install failed with return code: {e.returncode}")
        except (FileNotFoundError, OSError) as e:
            log.error(f"The network connection is down, or pip is not installed: {e}")
        

def update_txt(modules, output_path):
    '''A function that takes a 'set' of module names, sorts them, and overwrites 'modules.txt'.'''
    old_modules = set()
    new_modules = set(modules)
    final_modules = set()

    try:
        with open(output_path, "r", encoding="utf-8") as file:
            for module in file.readlines():
                old_modules.add(module.strip())
            final_modules = new_modules - old_modules
        
        with open(output_path, "w", encoding="utf-8") as file:
            for module in sorted(modules):
                file.write(f"{module}\n")
        
        pip_install(final_modules)
    except FileNotFoundError:
        with open(output_path, "w", encoding="utf-8") as file:
            for module in sorted(modules):
                file.write(f"{module}\n")
        pip_install(new_modules)


def start():
    '''Function to set up an observer and run a loop.'''
    root_check()
    w = Target()
    w.run()


if __name__ == "__main__":
    start()
