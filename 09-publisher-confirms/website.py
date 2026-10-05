"""Website: customers request rides here."""

import argparse

import pika

from common import connect, declare_rides, encode, new_ride, run_service


def main(log, args):
    connection = connect("website")
    channel = connection.channel()
    declare_rides(channel)
    # TODO(ex09): turn on publisher confirms if `args.confirms` is set. Without confirms, log the
    # rides that the broker returns.

    while True:
        ride = new_ride("website")
        properties = pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
        # TODO(ex09): publish with the mandatory flag if `args.mandatory` is set, and tell the customer
        # when the broker returns or refuses the ride.
        channel.basic_publish(exchange="rides", routing_key=f"ride.{ride['zone']}.{ride['type']}", body=encode(ride),
                              properties=properties)
        log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between ride requests")
    parser.add_argument("--confirms", action="store_true", help="use publisher confirms")
    parser.add_argument("--mandatory", action="store_true", help="publish with the mandatory flag")
    run_service("website", main, parser.parse_args())
