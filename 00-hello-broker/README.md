# Exercise 00: hello, broker

## What you'll learn

 * What a connection and a channel are, and how they show up in the management
   UI
 * That applications declare the AMQP model they need (queues, exchanges and
   bindings) themselves
 * How the default exchange delivers a message to the queue named by the
   routing key

## The taxi company so far

```
website --publish--> (default exchange) --"ride.requests"--> [ride.requests] --> manager

taxi t1, t2, t3, t4: on duty, but nobody sends them anything yet
```

 * `website.py` publishes a ride request every 2 seconds
 * `manager.py` consumes ride requests and decides which taxi should take each one
 * `taxi.py` runs once per taxi, and `run.py` starts one process for every taxi in `FLEET` (see `common.py`)

## Background

A **connection** is a TCP connection between your application and one RabbitMQ
node. It's expensive to open, so an application usually opens one and keeps it.

A **channel** is a lightweight session inside a connection. Every AMQP
operation (declaring a queue, publishing, consuming) happens on a channel. An
application can open many channels on one connection.

A message is never published straight into a queue. It's published to an
**exchange**, which decides which queues get a copy. The **default exchange**,
whose name is the empty string `""`, is special: every queue is bound to it
automatically, with the queue name as the binding key. Publishing to `""` with
routing key `ride.requests` therefore delivers the message to the queue named
`ride.requests`.

`queue_declare` creates the queue if it doesn't exist, and does nothing if it
already exists with the same properties. That's why both the website and the
manager declare `ride.requests`: whichever starts first creates it.

## Run it

```shell
cluster/cluster.sh up        # once, from the repository root
cluster/cluster.sh reset     # start from an empty broker
cd 00-hello-broker
python run.py
```

Open the management UI at http://localhost:15672 (user `guest`, password `guest`).

## Tasks

 1. Run the `basic` scenario. The website requests rides and the manager picks a taxi for each one, but the
    taxis go home straight away. Why?
 2. In the management UI, open the **Connections** and **Channels** tabs. How many connections are there,
    and which node is each one connected to? Find the connection names set in `common.py:connect()`
 3. Open the **Queues and Streams** tab and look at `ride.requests`. Stop the manager (or run only the website with
    `python website.py`) and watch the message count grow
 4. In `taxi.py`, declare a durable queue named `taxi.<id>` and start consuming from it with `on_ride`.
    Look for `TODO(ex00)`
 5. In `manager.py`, publish each ride to the queue of the taxi it was assigned to, using the default exchange
 6. Run the scenario again. For every `[manager] ... assigning taxi tN` line there should be a
    `[taxi tN] ... picking up` line for the same ride id. In the UI, each `taxi.<id>` queue should have a consumer

## Check

```
[website] ride 3f2a1c requested by Grace
[manager] ride 3f2a1c from website: assigning taxi t2
[taxi t2] ride 3f2a1c: picking up Grace
```

## Questions

 * The manager publishes on the same channel it consumes from. Would you use a second channel? Why?
 * What happens to a ride the manager sends to `taxi.t9`, a queue that doesn't exist? Try it with
   `python run.py ghost-taxi`
 * Who should declare `taxi.<id>`: the taxi, the manager, or both? What happens if the manager publishes
   before the taxi has started?

## Hints

<details>
<summary>Declaring and consuming</summary>

```python
queue = f"taxi.{args.id}"
channel.queue_declare(queue=queue, durable=True)
channel.basic_consume(queue=queue, on_message_callback=on_ride, auto_ack=True)
```
</details>

<details>
<summary>Publishing to the default exchange</summary>

```python
ch.basic_publish(exchange="", routing_key=f"taxi.{taxi_id}", body=body)
```
</details>

## Stretch goals

 * Open a second channel in the website and publish every other ride on it. Do you see it in the UI?
 * Start a second manager with `python manager.py` in another terminal. How are the ride requests shared
   between the two managers?

The solution is in `01-direct`.
