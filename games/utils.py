import os
import time

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

    class _Dummy:
        def __getattr__(self, _):
            return ""

    Fore = Back = Style = _Dummy()


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def color(text, fg="", bg="", bold=False):
    if not HAS_COLOR:
        return text
    prefix = ""
    if bold:
        prefix += Style.BRIGHT
    prefix += fg + bg
    return f"{prefix}{text}{Style.RESET_ALL}"


def header(title):
    clear()
    width = 50
    border = color("=" * width, Fore.CYAN, bold=True)
    title_line = color(f"  {title.center(width - 4)}  ", Fore.CYAN, bold=True)
    print(border)
    print(title_line)
    print(border)
    print()


def pause(msg="Appuyez sur Entrée pour continuer..."):
    input(color(f"\n{msg}", Fore.YELLOW))


def prompt(msg):
    return input(color(f"{msg}", Fore.GREEN))


def success(msg):
    print(color(f"✓ {msg}", Fore.GREEN, bold=True))


def error(msg):
    print(color(f"✗ {msg}", Fore.RED, bold=True))


def info(msg):
    print(color(f"  {msg}", Fore.CYAN))


def countdown(seconds=3):
    for i in range(seconds, 0, -1):
        print(color(f"  {i}...", Fore.YELLOW), end="\r", flush=True)
        time.sleep(1)
    print("  Go!   ")
    time.sleep(0.3)


def show_score(score, label="Score"):
    print(color(f"\n  {label}: ", Fore.WHITE) + color(str(score), Fore.YELLOW, bold=True))
