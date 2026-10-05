"""Audit: keeps a record of every ride requested, in any zone."""

from common import connect, decode, declare_rides, run_service


def main(log):
    connection = connect("audit")
    channel = connection.channel()
    declare_rides(channel)
    channel.queue_declare(queue="ride.audit", durable=True)
    channel.queue_bind(queue="ride.audit", exchange="rides", routing_key="ride.#")

    def on_ride(ch, method, properties, body):
        ride = decode(body)
        log.info("%s: ride %s for %s from %s", method.routing_key, ride["ride_id"], ride["customer"], ride["source"])

    channel.basic_consume(queue="ride.audit", on_message_callback=on_ride, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    run_service("audit", main)
