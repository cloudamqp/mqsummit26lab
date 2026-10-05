"""Manager: takes ride requests and assigns each one to a taxi."""

import argparse
import itertools

from common import FLEET, connect, decode, run_service


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
    channel.queue_declare(queue=queue, durable=True)
    # TODO(ex03): declare the topic exchange `rides` and bind `queue` to it so that it
    # receives the rides for this manager's zone, of any type.
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    pick_taxi = taxi_picker()

    def on_request(ch, method, properties, body):
        ride = decode(body)
        taxi_id = pick_taxi(ride)
        log.info("ride %s from %s: assigning taxi %s", ride["ride_id"], ride["source"], taxi_id)
        ch.basic_publish(exchange="taxi.dispatch", routing_key=taxi_id, body=body)

    channel.basic_consume(queue=queue, on_message_callback=on_request, auto_ack=True)
    log.info("waiting for ride requests in %s", args.zone)
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True, help="the zone this manager is responsible for")
    args = parser.parse_args()
    run_service(f"manager {args.zone}", main, args)
