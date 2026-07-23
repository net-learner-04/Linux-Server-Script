from rich.console import Console
from rich.table import Table
from rich.text import Text
import re, time, random, pyfiglet, os, pwd

console = Console()


def get_ascii_art_color():
    '''A function that returns random colors for use in ASCII art.'''
    color_list = [
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF",
    "#D7BAFF", "#E0BBE4", "#FEC8D8", "#FFDAC1", "#B5EAD7",
    "#C7CEEA", "#CDE7BE", "#F6DFEB", "#FBE7C6", "#A0E7E5",
    "#B4F8C8", "#D4F0F0", "#F9F7CF", "#E2F0CB", "#D0F4DE",
    "#F8C8DC", "#C9E4DE", "#D6EADF", "#E4C1F9", "#A9DEF9",
    "#FCF6BD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF"
    ]
    
    return random.choice(color_list)


def get_ascii_art():
    '''A function that returns the name of the currently logged-in user account as ASCII art.'''
    font_list = [
    "slant", "standard", "small",
    "mini", "digital", "letters",
    "cyberlarge", "cybermedium", "ogre",
    "rectangles", "caligraphy", "puffy",
    "shadow", "speed", "swan",
    "bubble", "chunky", "cooper",
    "epic", "fraktur", "fuzzy",
    "gothic", "isometric1", "italic",
    "katakana", "kontur", "larry3d",
    "lean", "lineblocks", "mnemonic",
    "pebble", "pepper", "poison",
    "rectangles", "relief", "relief2",
    "roman", "script", "serifcap",
    "shimrod", "short", "slant_relief",
    "slide", "soft", "starwars",
    "stresi", "sub-zero", "swirling",
    "twisted", "varsity", "wavy"
    ]
    
    username = pwd.getpwuid(os.getuid()).pw_name
    
    return pyfiglet.figlet_format(username, font=random.choice(font_list))
    
    
def colorize_usage(value):
    """Determines a warning color (red/yellow/green)
    based on a usage percentage value."""
    if value >= 80:
        return "bold red"
    elif value >= 60:
        return "bold yellow"
    return "bold green"


def build_weather_text(weather_data, city_name, uptime):
    """Builds a Rich Table block displaying weather information."""
    weather = weather_data.get("weather") or "Unknown"
    temp = weather_data.get("temp")
    feels_like = weather_data.get("feels_like")
    humidity = weather_data.get("humidity")

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left")
    table.add_column(justify="left")

    formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    table.add_row("[bold]Time:[/bold]", formatted)
    table.add_row("[bold]Uptime:[/bold]", uptime or "N/A")
    table.add_row("[bold]City:[/bold]", city_name)
    table.add_row("[bold]Weather:[/bold]", weather)

    if temp is not None and feels_like is not None:
        table.add_row(
            "[bold]Temp:[/bold]",
            f"{temp}°C (feels like {feels_like}°C)"
        )
    else:
        table.add_row("[bold]Temp:[/bold]", "N/A")

    if humidity is not None:
        table.add_row("[bold]Humidity:[/bold]", f"{humidity}%")
    else:
        table.add_row("[bold]Humidity:[/bold]", "N/A")

    return table


def build_system_text(system_data):
    """Builds a Rich Table block displaying server status information."""
    cpu = system_data.get("cpu")
    memory = system_data.get("memory")
    disk = system_data.get("disk")
    update_status = system_data.get("update_status") or ""
    last_login = system_data.get("last_login") or ""

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left")
    table.add_column(justify="left")

    if cpu is not None:
        style = colorize_usage(cpu)
        table.add_row("[bold]CPU:[/bold]", Text(f"{cpu}%", style=style))

    if memory is not None:
        style = colorize_usage(memory)
        table.add_row("[bold]Memory:[/bold]", Text(f"{memory}%", style=style))

    if disk is not None:
        style = colorize_usage(disk)
        table.add_row("[bold]Disk:[/bold]", Text(f"{disk}%", style=style))

    if update_status:
        style = "dim" if "up to date" in update_status else "bold yellow"
        table.add_row(
            "[bold]Updates:[/bold]",
            Text(update_status.replace("Update: ", ""), style=style)
        )

    if last_login:
        cleaned_login = last_login.replace("Last login: ", "")
        match = re.match(
            r"^(?P<time>.+?)\s*\((?P<user>[^:]+):\s*(?P<ip>[^)]+)\)$",
            cleaned_login
        )

        if match:
            table.add_row("[bold]Last Login:[/bold]", match.group("time"))
            table.add_row("[bold]User:[/bold]", match.group("user"))
            table.add_row("[bold]From:[/bold]", match.group("ip"))
        else:
            table.add_row("[bold]Last Login:[/bold]", cleaned_login)

    return table


def render(art, color, weather_data, system_data, city_name):
    """Arranges the ASCII art on top and positions weather/system info 
    blocks into 2 columns directly underneath."""
    art_text = Text(art.strip("\n"), style=color)
    console.print(art_text)

    weather_block = build_weather_text(
        weather_data,
        city_name,
        system_data.get("uptime")
    )
    system_block = build_system_text(system_data)

    bottom_layout = Table.grid(padding=(0, 8), expand=False)
    bottom_layout.add_column()
    bottom_layout.add_column()

    bottom_layout.add_row(
        weather_block,
        system_block
    )

    console.print(bottom_layout)
