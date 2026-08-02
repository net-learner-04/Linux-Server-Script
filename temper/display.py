from rich.table import Table
from rich import box
from logger import read_log

BLOCKS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def smooth(temps, window=3):
    '''Apply a simple moving average to reduce noise.'''
    if len(temps) < 2:
        return temps
    result = []
    for i in range(len(temps)):
        start = max(0, i - window + 1)
        chunk = temps[start:i + 1]
        result.append(sum(chunk) / len(chunk))
    return result


def draw_graph(dev_temps, width=30, min_range=5.0, use_smoothing=True):
    '''Receives a list of temperatures 
    and returns a graph string converted to block bars.'''
    if not dev_temps:
        return " " * width

    temps = [temp for _, temp in dev_temps[-width:]]

    if use_smoothing:
        temps = smooth(temps)

    min_temp, max_temp = min(temps), max(temps)

    # If the range is too small, force a minimum range so that
    # minor noise isn't exaggerated across the full graph width.
    if max_temp - min_temp < min_range:
        center = (max_temp + min_temp) / 2
        min_temp = center - min_range / 2
        max_temp = center + min_range / 2

    result = ""
    
    for temp in temps:
        index = round((temp - min_temp) / (max_temp - min_temp) * (len(BLOCKS) - 1))
        index = max(0, min(len(BLOCKS) - 1, index))
        result += BLOCKS[index]

    if len(result) < width:
        result = " " * (width - len(result)) + result
        
    return result


def render(dev_temps):
    '''Return the overall device temperature and graph in a 'Rich Table' format.'''
    table = Table(title="Thermometer",
                  title_justify="center",
                  title_style="bold white",
                  box=box.ROUNDED)
    table.add_column("Dev_name", justify="right", no_wrap=True)
    table.add_column("Current_temp", justify="center")
    table.add_column("Graph", justify="center")

    for device, temp in dev_temps.items():
        dev_name = device.replace(" ", "_").replace("/dev/", "")
        try:
            log_data = read_log(dev_name)
        except FileNotFoundError:
            log_data = []

        graph = draw_graph(log_data)
        table.add_row(dev_name, str(temp), graph)
        
    return table
