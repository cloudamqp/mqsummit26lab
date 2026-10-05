"""Ops: the control room sends alerts to the taxis."""

import argparse
import random

import pika

from common import connect, encode, run_service

ALERTS = [
    "Road works on Main Street, expect delays",
    "Heavy rain from 18:00",
    "The football match ends at 22:00, expect demand near the stadium",
    "Bridge closed for maintenance until midnight",
]


def main(log, args):
    connection = connect("ops")
    channel = connection.channel()
    # TODO(ex02): declare the fanout exchange `taxi.alerts`.

    while True:
        alert = {"text": random.choice(ALERTS)}
        properties = pika.BasicProperties(type="alert")
        # TODO(ex02): publish `alert` to `taxi.alerts` with `properties`.
        log.info("alert sent: %s", alert["text"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=8.0, help="seconds between alerts")
    run_service("ops", main, parser.parse_args())
