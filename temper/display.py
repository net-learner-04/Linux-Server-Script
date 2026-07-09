from rich.table import Table
from rich import box
from logger import read_log

BLOCKS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

def draw_graph(dev_temps, width=30):
    '''Receives a list of temperatures 
    and returns a graph string converted to block bars.'''
    if not dev_temps:
        return "No data."
    temps = [temp for _, temp in dev_temps[-width:]]
    min_temp, max_temp = min(temps), max(temps)
    if min_temp == max_temp:
        return BLOCKS[len(BLOCKS)//2] * len(temps)
    
    result = ""
    for temp in temps:
        index = round((temp - min_temp) / (max_temp - min_temp) * (len(BLOCKS) - 1))
        result += BLOCKS[index]
    return result

def render(dev_temps):
    '''Return the overall device temperature and graph in a 'Rich Table' format.'''
    table = Table(title="Thermometer", 
                  title_justify="center", 
                  title_style="bold white",
                  box=box.ROUNDED)
    table.add_column("Dev_name", justify="right", no_wrap=True)
    table.add_column("Current_temp", justify="center")
    table.add_column("Graph")
    for device, temp in dev_temps.items():
        dev_name = device.replace(" ", "_").replace("/dev/", "")
        try:
            log_data = read_log(dev_name)
        except FileNotFoundError:
            log_data = []
        
        graph = draw_graph(log_data)
        table.add_row(dev_name, str(temp), graph)
    return table
