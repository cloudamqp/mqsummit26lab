"""Audit: keeps a record of every ride requested, in any zone."""

from common import connect, decode, run_service


def main(log):
    connection = connect("audit")
    channel = connection.channel()
    channel.exchange_declare(exchange="rides", exchange_type="topic", durable=True)
    channel.queue_declare(queue="ride.audit", durable=True)
    # TODO(ex03): bind `ride.audit` to `rides` so that it receives every ride.

    def on_ride(ch, method, properties, body):
        ride = decode(body)
        log.info("%s: ride %s for %s from %s", method.routing_key, ride["ride_id"], ride["customer"], ride["source"])

    channel.basic_consume(queue="ride.audit", on_message_callback=on_ride, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    run_service("audit", main)
