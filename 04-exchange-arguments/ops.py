"""Ops: the control room sends alerts to the taxis."""

import argparse
import random

import pika

from common import FLEET, connect, encode, run_service

ALERTS = [
    "Road works on Main Street, expect delays",
    "Heavy rain from 18:00",
    "The football match ends at 22:00, expect demand near the stadium",
    "Bridge closed for maintenance until midnight",
]
# An alert goes to every taxi, to one taxi, or to the taxis in a zone or of a type.
TARGETS = ["all", *FLEET, *sorted({t["zone"] for t in FLEET.values()}), *sorted({t["type"] for t in FLEET.values()})]


def headers_for(target):
    if target in FLEET:
        return {"id": target}
    if any(t["zone"] == target for t in FLEET.values()):
        return {"zone": target}
    return {"type": target}


def main(log, args):
    connection = connect("ops")
    channel = connection.channel()
    channel.exchange_declare(exchange="taxi.alerts", exchange_type="fanout", durable=True)

    while True:
        target = args.to or random.choice(TARGETS)
        alert = {"text": random.choice(ALERTS), "to": target}
        if target == "all":
            properties = pika.BasicProperties(type="alert")
            channel.basic_publish(exchange="taxi.alerts", routing_key="", body=encode(alert), properties=properties)
        else:
            properties = pika.BasicProperties(type="alert", headers=headers_for(target))
            # TODO(ex04): publish `alert` to the headers exchange `taxi.notices` with `properties`.
            # Declare the exchange first.
        log.info("alert for %s: %s", target, alert["text"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=8.0, help="seconds between alerts")
    parser.add_argument("--to", choices=TARGETS, help="always send alerts to this target")
    run_service("ops", main, parser.parse_args())
