"""Manager: takes ride requests and assigns each one to a taxi."""

import argparse
import itertools
import time

import pika

from common import FLEET, connect, decode, declare_rides, run_service


def taxi_picker():
    """Return a function that picks a taxi for a ride, round-robin among the taxis of its zone and type."""
    turns = itertools.count()

    def pick(ride):
        matching = [t for t, taxi in FLEET.items() if taxi["zone"] == ride["zone"] and taxi["type"] == ride["type"]]
        return matching[next(turns) % len(matching)]

    return pick


def main(log, args):
    connection = connect(f"manager-{args.zone}")
    channel = connection.channel()
    queue = f"ride.requests.{args.zone}"
    # TODO(ex07): requests older than 30 s go to the exchange `rides.dlx`, and the queue holds
    # at most 5 requests.
    channel.queue_declare(queue=queue, durable=True, arguments={"x-queue-type": "quorum"})
    declare_rides(channel)
    channel.queue_bind(queue=queue, exchange="rides", routing_key=f"ride.{args.zone}.*")
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    pick_taxi = taxi_picker()

    replies = channel.queue_declare(queue="", exclusive=True).method.queue

    def on_status(ch, method, properties, body):
        status = decode(body)
        log.info("ride %s: taxi %s %s", status["ride_id"], status["taxi"], status["status"])

    channel.basic_consume(queue=replies, on_message_callback=on_status, auto_ack=True)

    def on_request(ch, method, properties, body):
        ride = decode(body)
        taxi_id = pick_taxi(ride)
        time.sleep(args.slow)
        log.info("ride %s from %s: assigning taxi %s", ride["ride_id"], ride["source"], taxi_id)
        ch.basic_publish(exchange="taxi.dispatch", routing_key=taxi_id, body=body,
                         properties=pika.BasicProperties(reply_to=replies))

    channel.basic_consume(queue=queue, on_message_callback=on_request, auto_ack=True)
    log.info("waiting for ride requests in %s", args.zone)
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True, help="the zone this manager is responsible for")
    parser.add_argument("--slow", type=float, default=0, help="seconds the manager needs to assign a ride")
    args = parser.parse_args()
    run_service(f"manager {args.zone}", main, args)
