"""Call centre: customers phone in and an operator requests the ride."""

import argparse
import itertools

import pika

from common import connect, declare_rides, encode, new_ride, run_service


def main(log, args):
    connection = connect("callcenter")
    channel = connection.channel()
    declare_rides(channel)

    rides = itertools.count(1)
    while True:
        ride = new_ride("callcenter")
        routing_key = f"ride.{ride['zone']}.{ride['type']}"
        log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        if args.broken_every and next(rides) % args.broken_every == 0:
            log.warning("ride %s: the operator forgot to fill in the type", ride["ride_id"])
            del ride["type"]
        properties = pika.BasicProperties(expiration="10000")
        channel.basic_publish(exchange="rides", routing_key=routing_key, body=encode(ride), properties=properties)
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between ride requests")
    parser.add_argument("--broken-every", type=int, default=0, metavar="N", help="send a broken request every Nth ride")
    run_service("callcenter", main, parser.parse_args())
