from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box
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
    font_list = ["soft", "varsity", "letters", "cyberlarge", "speed"]
    username = pwd.getpwuid(os.getuid()).pw_name
    return pyfiglet.figlet_format(username, font=random.choice(font_list))


def colorize_usage(value):
    """Determines a warning color (red/yellow/green) based on a usage percentage value."""
    if value >= 80:
        return "bold red"
    elif value >= 60:
        return "bold yellow"
    return "bold green"


def build_info_panel(weather_data, system_data, city_name):
    """Builds a single bordered table containing all info rows,
    split into 3 sections: weather / device+resource / login."""

    table = Table(
        box=box.ROUNDED,
        show_header=False,
        show_edge=True,
        pad_edge=True,
        padding=(0, 1),
        expand=False,
    )
    table.add_column(justify="left")
    table.add_column(justify="right")

    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    table.add_row("Time", formatted_time)
    table.add_row("Uptime", system_data.get("uptime") or "N/A")
    table.add_row("City", city_name or "N/A")
    table.add_row("Weather", weather_data.get("weather") or "Unknown")

    temp = weather_data.get("temp")
    feels_like = weather_data.get("feels_like")
    if temp is not None and feels_like is not None:
        table.add_row("Temp", f"{temp}°C (feels {feels_like}°C)")
    else:
        table.add_row("Temp", "N/A")

    humidity = weather_data.get("humidity")
    table.add_row("Humidity", f"{humidity}%" if humidity is not None else "N/A")

    table.add_section()

    kernel = system_data.get("kernel")
    os_name = system_data.get("os_name")
    hostname = system_data.get("hostname")

    if hostname:
        table.add_row("Hostname", hostname)
    if os_name:
        table.add_row("OS", os_name)
    if kernel:
        table.add_row("Kernel", kernel)

    cpu = system_data.get("cpu")
    memory = system_data.get("memory")
    disk = system_data.get("disk")
    update_status = system_data.get("update_status") or ""

    if cpu is not None:
        table.add_row("CPU", Text(f"{cpu}%", style=colorize_usage(cpu)))
    if memory is not None:
        table.add_row("Memory", Text(f"{memory}%", style=colorize_usage(memory)))
    if disk is not None:
        table.add_row("Disk", Text(f"{disk}%", style=colorize_usage(disk)))

    if update_status:
        style = "dim" if "up to date" in update_status else "bold yellow"
        table.add_row("Updates", Text(update_status.replace("Update: ", ""), style=style))

    table.add_section()
-
    last_login = system_data.get("last_login") or ""
    if last_login:
        cleaned_login = last_login.replace("Last login: ", "")
        match = re.match(
            r"^(?P<time>.+?)\s*\((?P<user>[^:]+):\s*(?P<ip>[^)]+)\)$",
            cleaned_login
        )
        if match:
            table.add_row("Last Login", match.group("time"))
            table.add_row("User", match.group("user"))
            table.add_row("From", match.group("ip"))
        else:
            table.add_row("Last Login", cleaned_login)

    return table


def render(art, color, weather_data, system_data, city_name):
    """Renders ASCII art on top, and a single bordered info box
    (weather + system merged) directly underneath."""
    art_text = Text(art.strip("\n"), style=color)
    console.print(art_text)

    info_panel = build_info_panel(weather_data, system_data, city_name)
    console.print(info_panel)
