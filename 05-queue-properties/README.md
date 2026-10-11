# Exercise 05: queue properties and persistent messages

This exercise is optional.

## What you'll learn

 * The difference between durable, exclusive and auto-delete queues, and when to use each
 * How to let the broker choose a queue name, and how to use it for replies
 * What a persistent message is, and what happens to queues and messages when a node restarts

## The taxi company so far

```
website, callcenter ─> (rides) ─> [ride.requests.<zone>] ─> manager ─> (taxi.dispatch) ─> [taxi.<id>] ─> taxi
                          └─(alternate exchange)─> (rides.unrouted) ─> [ride.unassigned] ─> partner
ops ─> (taxi.alerts, fanout) and (taxi.notices, headers) ─> [taxi.<id>]

new:   taxi ─> (default) ─"amq.gen-..."─> [amq.gen-..., exclusive] ─> manager
```

The manager wants to know which taxis accepted their rides. Each manager instance needs its own queue for the
replies, and that queue is only useful while that instance is running.

## Background

`queue_declare` takes three flags that decide the lifetime of a queue:

 * `durable=True`: the queue definition survives a broker restart. All the queues so far are durable
 * `exclusive=True`: the queue belongs to the connection that declared it. Other connections can't use it,
   and the broker deletes it when that connection closes
 * `auto_delete=True`: the broker deletes the queue when its last consumer goes away

If you declare a queue with the name `""`, the broker picks a unique name such as `amq.gen-JzTY20BRgKO-HjmUJj0wLg`
and returns it in the reply: `channel.queue_declare(queue="", exclusive=True).method.queue`.

Separately, each message is either **persistent** (`delivery_mode=2`) or **transient**. A durable classic queue
keeps its persistent messages across a restart, and drops the transient ones. A durable queue is required for
this. A persistent message in a non-durable queue is still lost.

The `reply_to` property is the usual way to tell a consumer where to send a reply. RabbitMQ doesn't do anything
with it. It's a convention between the two applications.

## Run it

```shell
cluster/cluster.sh reset
cd 05-queue-properties
python run.py
```

## Tasks

 1. In `manager.py`, declare an exclusive queue with a broker-chosen name, store its name in `replies`, and consume
    from it with `on_status`
 2. In `taxi.py`, send `status` to the queue named in `reply_to`, through the default exchange
 3. Run the scenario and find the reply queues in the UI. Which flags do they show? Stop the scenario: what
    happens to them?
 4. In `website.py`, make the ride messages persistent. Leave `callcenter.py` as it is
 5. Make some rides pile up and restart the node that holds them:
    1. `python run.py --for 10`, so that every queue is declared
    2. `python run.py no-managers --for 30`, so that rides accumulate
    3. `../cluster/cluster.sh queues`: note the messages in `ride.requests.north` and the node it's on (`leader`)
    4. `../cluster/cluster.sh stop-node N` for that node, then `../cluster/cluster.sh queues` again
    5. `../cluster/cluster.sh start-node N`, then `../cluster/cluster.sh queues` again. How many rides are left? Whose?
 6. Stop the node holding `ride.requests.north` again and run `python run.py`. What happens to the north manager?
    And to the rides requested in the north while the node is down? Start the node again before moving on

On a CloudAMQP free plan, the broker has a single node that you can't stop, so tasks 5 and 6 need the local cluster. Follow them
on the facilitator's screen, or do them on the local cluster if you have Docker.

## Check

```
[manager north] ride 4b19aa from website: assigning taxi t1
[taxi t1] ride 4b19aa: picking up Barbara in north
[manager north] ride 4b19aa: taxi t1 accepted
```

## Questions

 * Why should the reply queue be exclusive rather than durable?
 * Every manager in a zone shares `ride.requests.<zone>`, but each one has its own reply queue. Why?
 * In task 6, the rides for the north zone were neither delivered nor stored. Which part of the architecture
   would you change to avoid that? Exercise 06 answers this

## Hints

<details>
<summary>Reply queue</summary>

```python
replies = channel.queue_declare(queue="", exclusive=True).method.queue
channel.basic_consume(queue=replies, on_message_callback=on_status, auto_ack=True)
```
</details>

<details>
<summary>Replying and persistent messages</summary>

```python
if properties.reply_to:
    ch.basic_publish(exchange="", routing_key=properties.reply_to, body=encode(status))
```

```python
properties = pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
```
</details>

## Stretch goals

 * Give each taxi an exclusive, auto-delete queue, bound to `taxi.alerts`, for alerts only. What happens to alerts sent
   while a taxi is off duty? Why does RabbitMQ 4.3 refuse the queue if it's neither durable nor exclusive?

The solution is in `06-quorum-queues`.
