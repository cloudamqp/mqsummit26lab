"""Call centre: customers phone in and an operator requests the ride."""

import argparse

from common import connect, declare_rides, encode, new_ride, run_service


def main(log, args):
    connection = connect("callcenter")
    channel = connection.channel()
    declare_rides(channel)

    while True:
        ride = new_ride("callcenter")
        # TODO(ex07): a customer on the phone waits 10 s at most. Make the request expire after that.
        channel.basic_publish(exchange="rides", routing_key=f"ride.{ride['zone']}.{ride['type']}", body=encode(ride))
        log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between ride requests")
    run_service("callcenter", main, parser.parse_args())
