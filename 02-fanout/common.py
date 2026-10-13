"""Helpers shared by every service of the taxi company."""

import json
import logging
import os
import random
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pika

# The broker to connect to: one URL, amqp://USER:PASSWORD@HOST/VHOST (amqps:// for TLS). To use another broker, set
# RABBITMQ_URL in broker.env at the root of the repository, or in the environment (see the README).
DEFAULT_URL = "amqp://guest:guest@localhost/%2F"
BROKER_ENV = Path(__file__).resolve().parent.parent / "broker.env"
LOCAL_PORTS = (5672, 5673, 5674)  # the 3 nodes of the local cluster

# run.py starts one taxi process per entry.
FLEET = ["t1", "t2", "t3", "t4"]
CUSTOMERS = ["Ada", "Alan", "Barbara", "Donald", "Edsger", "Grace", "Joe", "Ken", "Radia", "Tim"]


def broker_url():
    """RABBITMQ_URL from the environment, else from broker.env, else the local cluster."""
    url = os.environ.get("RABBITMQ_URL")
    if not url and BROKER_ENV.exists():
        for line in BROKER_ENV.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "RABBITMQ_URL":
                url = value.strip()
    return url or DEFAULT_URL


def broker_urls():
    """The URL of each node. A localhost URL without a port stands for the 3 nodes of the local cluster."""
    url = urlsplit(broker_url())
    if url.hostname not in ("localhost", "127.0.0.1") or url.port:
        return [url.geturl()]
    credentials = url.netloc.rpartition("@")[0]
    prefix = f"{credentials}@" if credentials else ""
    return [url._replace(netloc=f"{prefix}{url.hostname}:{port}").geturl() for port in LOCAL_PORTS]


def connect(service_name):
    """Open a connection to one of the broker's URLs, trying them in random order."""
    urls = broker_urls()
    parameters = []
    for url in random.sample(urls, len(urls)):
        params = pika.URLParameters(url)
        params.client_properties = {"connection_name": service_name}
        parameters.append(params)
    return pika.BlockingConnection(parameters)


def new_ride(source):
    return {
        "ride_id": uuid.uuid4().hex[:6],
        "source": source,
        "customer": random.choice(CUSTOMERS),
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
