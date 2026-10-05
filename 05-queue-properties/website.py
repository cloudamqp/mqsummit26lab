"""Website: customers request rides here."""

import argparse

from common import connect, declare_rides, encode, new_ride, run_service


def main(log, args):
    connection = connect("website")
    channel = connection.channel()
    declare_rides(channel)

    while True:
        ride = new_ride("website")
        # TODO(ex05): make the message persistent.
        channel.basic_publish(exchange="rides", routing_key=f"ride.{ride['zone']}.{ride['type']}", body=encode(ride))
        log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between ride requests")
    run_service("website", main, parser.parse_args())
