"""Customer support: tells customers when the company couldn't serve their ride."""

from common import connect, decode, run_service


def main(log):
    connection = connect("support")
    channel = connection.channel()
    channel.exchange_declare(exchange="rides.dlx", exchange_type="fanout", durable=True)
    channel.queue_declare(queue="ride.dead", durable=True, arguments={"x-queue-type": "quorum"})
    channel.queue_bind(queue="ride.dead", exchange="rides.dlx")

    def on_dead_ride(ch, method, properties, body):
        ride = decode(body)
        headers = properties.headers or {}
        log.info("sorry %s, we couldn't serve ride %s (%s from %s)", ride["customer"], ride["ride_id"],
                 headers.get("x-first-death-reason"), headers.get("x-first-death-queue"))

    channel.basic_consume(queue="ride.dead", on_message_callback=on_dead_ride, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    run_service("support", main)
