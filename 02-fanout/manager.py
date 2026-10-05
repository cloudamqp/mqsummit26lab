"""Manager: takes ride requests and assigns each one to a taxi."""

import argparse
import itertools

from common import FLEET, connect, decode, run_service


def main(log, args):
    connection = connect("manager")
    channel = connection.channel()
    channel.queue_declare(queue="ride.requests", durable=True)
    channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
    taxis = itertools.cycle(FLEET)

    def on_request(ch, method, properties, body):
        ride = decode(body)
        taxi_id = next(taxis)
        log.info("ride %s from %s: assigning taxi %s", ride["ride_id"], ride["source"], taxi_id)
        ch.basic_publish(exchange="taxi.dispatch", routing_key=taxi_id, body=body)

    channel.basic_consume(queue="ride.requests", on_message_callback=on_request, auto_ack=True)
    log.info("waiting for ride requests")
    channel.start_consuming()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    run_service("manager", main, parser.parse_args())
