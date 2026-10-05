"""Start the taxi company services for a scenario. Ctrl-C stops all of them.

    python run.py                 # the "basic" scenario
    python run.py --list          # list scenarios
    python run.py basic --for 20  # stop after 20 seconds
    python run.py --without t3    # leave out every command that contains "t3"
"""

import argparse
import itertools
import subprocess
import sys
import threading
import time
from pathlib import Path

from common import FLEET

TAXIS = [("taxi.py", "--id", taxi_id) for taxi_id in FLEET]

# Each scenario is a list of commands: a script followed by its arguments.
# Services start in the listed order, so consumers come before producers.
SCENARIOS = {
    "basic": [
        *TAXIS,
        ("manager.py",),
        ("website.py",),
        ("callcenter.py",),
    ],
    "ghost-taxi": [
        *TAXIS,
        ("manager.py", "--taxis", "t1,t2,t3,t4,t9"),
        ("website.py",),
    ],
}

COLOURS = ["\033[36m", "\033[33m", "\033[35m", "\033[32m", "\033[34m", "\033[91m", "\033[96m", "\033[93m"]
RESET = "\033[0m"


def stream(process, colour, lock):
    for line in process.stdout:
        with lock:
            sys.stdout.write(f"{colour}{line}{RESET}" if sys.stdout.isatty() else line)
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", nargs="?", default="basic", choices=SCENARIOS)
    parser.add_argument("--list", action="store_true", help="list the scenarios and exit")
    parser.add_argument("--for", dest="duration", type=float, help="stop after this many seconds")
    parser.add_argument("--without", action="append", default=[], metavar="TEXT",
                        help="leave out the commands that contain TEXT (can be repeated)")
    args = parser.parse_args()

    if args.list:
        for name, commands in SCENARIOS.items():
            print(f"{name}:")
            for command in commands:
                print("   ", " ".join(command))
        return

    here = Path(__file__).parent
    lock = threading.Lock()
    processes = []
    commands = [c for c in SCENARIOS[args.scenario] if not any(t in " ".join(c) for t in args.without)]
    for command, colour in zip(commands, itertools.cycle(COLOURS)):
        process = subprocess.Popen(
            [sys.executable, "-u", *command], cwd=here, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        threading.Thread(target=stream, args=(process, colour, lock), daemon=True).start()
        processes.append((command, process))
        time.sleep(0.3)

    deadline = time.monotonic() + args.duration if args.duration else None
    running = {process.pid for _, process in processes}
    try:
        while running and (deadline is None or time.monotonic() < deadline):
            for command, process in processes:
                if process.pid in running and process.poll() is not None:
                    running.discard(process.pid)
                    print(f"[runner] {' '.join(command)} exited with code {process.returncode}", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        for _, process in processes:
            process.terminate()
        for _, process in processes:
            process.wait()


if __name__ == "__main__":
    main()
