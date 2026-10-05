"""Taxi: one process per car. Receives the rides the manager assigns to it."""

import argparse

from common import FLEET, connect, decode, run_service


def main(log, args):
    connection = connect(f"taxi-{args.id}")
    channel = connection.channel()

    def on_message(ch, method, properties, body):
        message = decode(body)
        if properties.type == "alert":
            log.info("alert: %s", message["text"])
            return
        log.info("ride %s: picking up %s", message["ride_id"], message["customer"])

    queue = f"taxi.{args.id}"
    channel.queue_declare(queue=queue, durable=True)
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.dispatch", routing_key=args.id)
    # TODO(ex02): declare the fanout exchange `taxi.alerts` and bind `queue` to it.
    channel.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=True)

    log.info("on duty")
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=FLEET)
    args = parser.parse_args()
    run_service(f"taxi {args.id}", main, args)
