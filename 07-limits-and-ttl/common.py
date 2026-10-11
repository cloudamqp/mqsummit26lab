"""Helpers shared by every service of the taxi company."""

import json
import logging
import os
import random
import sys
import time
import uuid
from pathlib import Path

import pika
from pika.exceptions import AMQPConnectionError

# The broker to connect to. To use another one, set RABBITMQ_URL in broker.env at the root of the repository, or in
# the environment (see the README). Several URLs, separated by commas, are tried in random order.
DEFAULT_URL = ",".join(f"amqp://guest:guest@localhost:{port}/%2F" for port in (5672, 5673, 5674))
BROKER_ENV = Path(__file__).resolve().parent.parent / "broker.env"

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


def broker_urls():
    """The broker's AMQP URLs: RABBITMQ_URL from the environment, else from broker.env, else the local cluster."""
    url = os.environ.get("RABBITMQ_URL")
    if not url and BROKER_ENV.exists():
        for line in BROKER_ENV.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "RABBITMQ_URL":
                url = value.strip()
    return [u.strip() for u in (url or DEFAULT_URL).split(",") if u.strip()]


def connect(service_name):
    """Open a connection to one of the broker's URLs, trying them in random order."""
    urls = broker_urls()
    parameters = []
    for url in random.sample(urls, len(urls)):
        params = pika.URLParameters(url)
        params.client_properties = {"connection_name": service_name}
        parameters.append(params)
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
