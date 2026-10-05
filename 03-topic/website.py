"""Website: customers request rides here."""

import argparse

from common import connect, encode, new_ride, run_service


def main(log, args):
    connection = connect("website")
    channel = connection.channel()
    # TODO(ex03): declare the topic exchange `rides` and stop declaring `ride.requests`.
    channel.queue_declare(queue="ride.requests", durable=True)

    while True:
        ride = new_ride("website")
        # TODO(ex03): publish to `rides` with the routing key `ride.<zone>.<type>`.
        channel.basic_publish(exchange="", routing_key="ride.requests", body=encode(ride))
        log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between ride requests")
    run_service("website", main, parser.parse_args())
