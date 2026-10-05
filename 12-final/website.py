"""Website: customers request rides here."""

import argparse

import pika
from pika.exceptions import NackError, UnroutableError

from common import connect, declare_rides, decode, encode, new_ride, run_service


def main(log, args):
    connection = connect("website")
    channel = connection.channel()
    declare_rides(channel)
    if args.confirms:
        channel.confirm_delivery()
    else:
        channel.add_on_return_callback(lambda ch, method, properties, body: log.warning(
            "ride %s returned by the broker: %s", decode(body)["ride_id"], method.reply_text))

    while True:
        ride = new_ride("website")
        properties = pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
        try:
            channel.basic_publish(exchange="rides", routing_key=f"ride.{ride['zone']}.{ride['type']}",
                                  body=encode(ride), properties=properties, mandatory=args.mandatory)
            log.info("ride %s requested by %s in %s (%s)", ride["ride_id"], ride["customer"], ride["zone"], ride["type"])
        except UnroutableError:
            log.warning("ride %s: sorry %s, we don't serve %s", ride["ride_id"], ride["customer"], ride["zone"])
        except NackError:
            log.warning("ride %s: sorry %s, we're too busy, try again later", ride["ride_id"], ride["customer"])
        connection.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between ride requests")
    parser.add_argument("--confirms", action="store_true", help="use publisher confirms")
    parser.add_argument("--mandatory", action="store_true", help="publish with the mandatory flag")
    run_service("website", main, parser.parse_args())
