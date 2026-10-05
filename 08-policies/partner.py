"""Partner: another taxi company that takes the rides we can't serve."""

from common import connect, decode, run_service


def main(log):
    connection = connect("partner")
    channel = connection.channel()
    channel.queue_declare(queue="ride.unassigned", durable=True)
    channel.exchange_declare(exchange="rides.unrouted", exchange_type="fanout", durable=True, internal=True)
    channel.queue_bind(queue="ride.unassigned", exchange="rides.unrouted")

    def on_ride(ch, method, properties, body):
        ride = decode(body)
        log.info("ride %s in %s handed over to a partner company", ride["ride_id"], ride["zone"])

    channel.basic_consume(queue="ride.unassigned", on_message_callback=on_ride, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    run_service("partner", main)
