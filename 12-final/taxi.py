"""Taxi: one process per car. Receives the rides the manager assigns to it."""

import argparse
import itertools
import os

from common import FLEET, connect, decode, encode, run_service


def main(log, args):
    connection = connect(f"taxi-{args.id}")
    channel = connection.channel()

    rides = itertools.count(1)

    def on_message(ch, method, properties, body):
        message = decode(body)
        if properties.type == "alert":
            log.info("alert for %s: %s", message["to"], message["text"])
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        if args.on_break:
            log.info("ride %s: on a break, returning it for later (redelivered: %s)",
                     message["ride_id"], method.redelivered)
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
            return
        if args.crash_every and next(rides) % args.crash_every == 0:
            log.error("ride %s: the taxi broke down", message["ride_id"])
            os._exit(1)
        log.info("ride %s: picking up %s in %s (redelivered: %s)",
                 message["ride_id"], message["customer"], message["zone"], method.redelivered)
        status = {"ride_id": message["ride_id"], "taxi": args.id, "status": "accepted"}
        if properties.reply_to:
            ch.basic_publish(exchange="", routing_key=properties.reply_to, body=encode(status))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    queue = f"taxi.{args.id}"
    channel.queue_declare(queue=queue, durable=True, arguments={"x-queue-type": "quorum"})
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.dispatch", routing_key=args.id)
    channel.exchange_declare(exchange="taxi.alerts", exchange_type="fanout", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.alerts")
    taxi = FLEET[args.id]
    channel.exchange_declare(exchange="taxi.notices", exchange_type="headers", durable=True)
    channel.queue_bind(queue=queue, exchange="taxi.notices",
                       arguments={"x-match": "any", "id": args.id, "zone": taxi["zone"], "type": taxi["type"]})
    channel.basic_consume(queue=queue, on_message_callback=on_message)

    log.info("on duty in %s (%s)", taxi["zone"], taxi["type"])
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=FLEET)
    parser.add_argument("--crash-every", type=int, default=0, metavar="N", help="break down on every Nth ride")
    parser.add_argument("--on-break", action="store_true", help="refuse every ride")
    args = parser.parse_args()
    run_service(f"taxi {args.id}", main, args)
