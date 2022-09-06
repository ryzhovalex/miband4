import os
import sys

from .miband4_console import MiConsole 
from .quick_call import call_quick


def main() -> None:
    try:
        mode = sys.argv[1]
    except IndexError:
        # Set quick mode by default.
        mode = "q"

    with open(os.path.dirname(__file__) + "/creds") as file:
        mac, auth = file.readline().strip().split(";")

    if mode == "q":
        call_quick(mac)
    elif mode == "c":
        MiConsole(mac, auth)


if __name__ == "__main__":
    main()