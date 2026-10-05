"""Taxi: one process per car. Receives the rides the manager assigns to it."""

import argparse

from common import FLEET, connect, decode, run_service


def main(log, args):
    connection = connect(f"taxi-{args.id}")
    channel = connection.channel()

    def on_ride(ch, method, properties, body):
        ride = decode(body)
        log.info("ride %s: picking up %s", ride["ride_id"], ride["customer"])

    queue = f"taxi.{args.id}"
    channel.queue_declare(queue=queue, durable=True)
    # TODO(ex01): declare the direct exchange `taxi.dispatch` and bind `queue` to it with the taxi id.
    channel.basic_consume(queue=queue, on_message_callback=on_ride, auto_ack=True)

    log.info("on duty")
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=FLEET)
    args = parser.parse_args()
    run_service(f"taxi {args.id}", main, args)
