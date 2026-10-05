"""Helpers shared by every service of the taxi company."""

import json
import logging
import random
import sys
import time
import uuid

import pika
from pika.exceptions import AMQPConnectionError

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
    channel.exchange_declare(exchange="rides", exchange_type="topic", durable=True)


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
    """Run `main(log, *args)` and reconnect when the connection to the broker is lost."""
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    log = logging.getLogger(name)
    while True:
        try:
            main(log, *args)
            return
        except KeyboardInterrupt:
            return
        except AMQPConnectionError as e:
            log.warning("connection lost (%r), reconnecting in 2 s", e)
            time.sleep(2)
