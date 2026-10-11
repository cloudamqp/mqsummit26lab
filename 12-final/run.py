"""Start the taxi company services for a scenario. Ctrl-C stops all of them.

    python run.py                 # the "basic" scenario
    python run.py --list          # list scenarios
    python run.py basic --for 20  # stop after 20 seconds
    python run.py --without t3    # leave out every command that contains "t3"

A service that crashes (exits with an error) is started again after 1 s, as a supervisor such as systemd or
Kubernetes would do.
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
        ("manager.py", "--zone", "north"),
        ("manager.py", "--zone", "south"),
        ("partner.py",),
        ("support.py",),
        ("website.py",),
        ("callcenter.py",),
        ("ops.py",),
    ],
    "no-managers": [
        ("website.py",),
        ("callcenter.py",),
    ],
    "crashing-taxi": [
        ("taxi.py", "--id", "t1", "--crash-every", "2"),
        ("taxi.py", "--id", "t2"),
        ("manager.py", "--zone", "north"),
        ("website.py", "--interval", "1"),
    ],
    "taxi-on-break": [
        ("taxi.py", "--id", "t1", "--on-break"),
        ("taxi.py", "--id", "t2"),
        ("manager.py", "--zone", "north"),
        ("support.py",),
        ("website.py", "--interval", "1"),
    ],
    "two-managers": [
        *TAXIS,
        ("manager.py", "--zone", "north", "--slow", "4", "--instance", "slow"),
        ("manager.py", "--zone", "north", "--slow", "0.5", "--instance", "fast"),
        ("website.py", "--interval", "0.5"),
    ],
    "broken-rides": [
        *TAXIS,
        ("manager.py", "--zone", "north"),
        ("manager.py", "--zone", "south"),
        ("support.py",),
        ("callcenter.py", "--interval", "2", "--broken-every", "3"),
    ],
    "audit": [
        *TAXIS,
        ("manager.py", "--zone", "north"),
        ("manager.py", "--zone", "south"),
        ("audit.py",),
        ("partner.py",),
        ("website.py",),
        ("callcenter.py",),
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

    def start(command, colour):
        process = subprocess.Popen(
            [sys.executable, "-u", *command], cwd=here, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        threading.Thread(target=stream, args=(process, colour, lock), daemon=True).start()
        return process

    processes = []  # [command, colour, process]
    commands = [c for c in SCENARIOS[args.scenario] if not any(t in " ".join(c) for t in args.without)]
    for command, colour in zip(commands, itertools.cycle(COLOURS)):
        processes.append([command, colour, start(command, colour)])
        time.sleep(0.3)

    deadline = time.monotonic() + args.duration if args.duration else None
    running = {process.pid for _, _, process in processes}
    try:
        while running and (deadline is None or time.monotonic() < deadline):
            for entry in processes:
                command, colour, process = entry
                if process.pid in running and process.poll() is not None:
                    running.discard(process.pid)
                    if process.returncode == 0:
                        print(f"[runner] {' '.join(command)} exited", flush=True)
                        continue
                    print(f"[runner] {' '.join(command)} crashed (exit code {process.returncode}), "
                          "restarting it in 1 s", flush=True)
                    time.sleep(1)
                    entry[2] = start(command, colour)
                    running.add(entry[2].pid)
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        for _, _, process in processes:
            process.terminate()
        for _, _, process in processes:
            process.wait()


if __name__ == "__main__":
    main()
