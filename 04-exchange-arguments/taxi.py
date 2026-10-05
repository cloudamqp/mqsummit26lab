"""Taxi: one process per car. Receives the rides the manager assigns to it."""

import argparse

from common import FLEET, connect, decode, run_service


def main(log, args):
    connection = connect(f"taxi-{args.id}")
    channel = connection.channel()

    def on_message(ch, method, properties, body):
        message = decode(body)
        if properties.type == "alert":
            log.info("alert for %s: %s", message["to"], message["text"])
            return
        log.info("ride %s: picking up %s in %s", message["ride_id"], message["customer"], message["zone"])

    queue = f"taxi.{args.id}"
    channel.queue_declare(queue=queue, durable=True)
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.dispatch", routing_key=args.id)
    channel.exchange_declare(exchange="taxi.alerts", exchange_type="fanout", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.alerts")
    # TODO(ex04): declare the headers exchange `taxi.notices` and bind `queue` to it so that the taxi
    # receives the alerts whose headers name its id, its zone or its type.
    channel.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=True)

    log.info("on duty in %s (%s)", FLEET[args.id]["zone"], FLEET[args.id]["type"])
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=FLEET)
    args = parser.parse_args()
    run_service(f"taxi {args.id}", main, args)
