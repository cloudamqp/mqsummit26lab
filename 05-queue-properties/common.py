"""Helpers shared by every service of the taxi company."""

import json
import logging
import random
import sys
import uuid

import pika

NODES = [("localhost", 5672), ("localhost", 5673), ("localhost", 5674)]
CREDENTIALS = pika.PlainCredentials("guest", "guest")

# run.py starts one taxi process per entry.
FLEET = {
    "t1": {"zone": "north", "type": "sedan"},
    "t2": {"zone": "north", "type": "van"},
    "t3": {"zone": "south", "type": "sedan"},
    "t4": {"zone": "south", "type": "van"},
}
# Customers can request rides in every zone, but no taxi serves "east" yet.
ZONES = ["north", "south", "east"]
CUSTOMERS = ["Ada", "Alan", "Barbara", "Donald", "Edsger", "Grace", "Joe", "Ken", "Radia", "Tim"]


def connect(service_name):
    """Open a connection to one of the cluster nodes, trying them in random order."""
    nodes = random.sample(NODES, len(NODES))
    parameters = [
        pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=CREDENTIALS,
            client_properties={"connection_name": service_name},
        )
        for host, port in nodes
    ]
    return pika.BlockingConnection(parameters)


def declare_rides(channel):
    channel.exchange_declare(exchange="rides", exchange_type="topic", durable=True,
                             arguments={"alternate-exchange": "rides.unrouted"})


def new_ride(source):
    return {
        "ride_id": uuid.uuid4().hex[:6],
        "source": source,
        "customer": random.choice(CUSTOMERS),
        "zone": random.choice(ZONES),
        "type": random.choice(["sedan", "van"]),
    }


def encode(message):
    return json.dumps(message).encode()


def decode(body):
    return json.loads(body)


def run_service(name, main, *args):
    """Set up logging and run `main(log, *args)` until it returns or Ctrl-C is pressed."""
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    try:
        main(logging.getLogger(name), *args)
    except KeyboardInterrupt:
        pass
