# Exercise 02: fanout exchange

## What you'll learn

 * How a fanout exchange delivers a copy of every message to every bound queue
 * That one queue can be bound to several exchanges, and receives messages from all of them
 * How a consumer can tell different kinds of messages apart using message properties

## The taxi company so far

```
website    ─┐
callcenter ─┴─> [ride.requests] ─> manager ─> (taxi.dispatch, direct) ─"t2"─> [taxi.t2] ─> taxi t2

ops ─> (taxi.alerts, fanout) ─> ??? (nothing is bound yet)
```

`ops.py` is new. It represents the control room, and it sends an alert every 8 seconds that every taxi on
duty should receive.

## Background

A **fanout exchange** ignores the routing key. It delivers a copy of every message to every queue bound to
it. It's the simplest way to broadcast.

A queue doesn't belong to an exchange. Each taxi queue is already bound to the default exchange and to
`taxi.dispatch`, and it can be bound to as many other exchanges as needed. The consumer reads one stream of
messages, so it needs a way to tell rides from alerts. Here, ops sets the `type` message property to `alert`.
A message has a set of standard properties (`content_type`, `type`, `message_id`, `timestamp`,
`delivery_mode` and others), plus a `headers` table for anything application-specific.

## Run it

```shell
cluster/cluster.sh reset
cd 02-fanout
python run.py
```

## Tasks

 1. In `ops.py`, declare a durable fanout exchange named `taxi.alerts` and publish each alert to it with the
    `properties` already prepared. Which routing key will you use?
 2. In `taxi.py`, declare the same exchange and bind the taxi queue to it
 3. Check that every alert reaches every taxi:
    1. Run `python run.py --for 30 | grep alert`. Each `[ops] alert sent` line should be followed by an `alert:`
       line from each of the 4 taxis, as in the "Check" section below
    2. In the management UI, open the `taxi.alerts` exchange. How many queues are bound to it? Compare its
       "Publish (In)" and "Publish (Out)" rates
 4. Change the routing key in `ops.py` to `t1`. Which taxis receive the alert now?
 5. Run the scenario without one taxi (`python run.py --without t3`). What happens to the alerts for `t3`
    while it's away? Start it by hand with `python taxi.py --id t3`. What happens when it comes back?

## Check

```
[ops] alert sent: Heavy rain from 18:00
[taxi t1] alert: Heavy rain from 18:00
[taxi t2] alert: Heavy rain from 18:00
[taxi t3] alert: Heavy rain from 18:00
[taxi t4] alert: Heavy rain from 18:00
```

## Questions

 * Could you have sent the alert using `taxi.dispatch` (the direct exchange) instead? With how many publishes,
   and who would need to know the list of taxis?
 * A new taxi `t5` joins the fleet. What has to change in ops for `t5` to get the alerts?
 * Is an alert published while a taxi is off duty still useful once the taxi is back? Keep the answer in mind
   for exercise 07

## Hints

<details>
<summary>Declaring and publishing</summary>

```python
channel.exchange_declare(exchange="taxi.alerts", exchange_type="fanout", durable=True)
channel.basic_publish(exchange="taxi.alerts", routing_key="", body=encode(alert), properties=properties)
```
</details>

## Stretch goals

 * Write a `dashboard.py` service with an exclusive, server-named queue (`queue=""`, `exclusive=True`) bound
   to `taxi.alerts`. What happens to its queue when the dashboard stops?

The solution is in `03-topic`.
