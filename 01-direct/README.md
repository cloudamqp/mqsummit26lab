# Exercise 01: direct exchange

## What you'll learn

 * How to declare an exchange and bind a queue to it
 * How a direct exchange routes messages by comparing the routing key with the binding key
 * What happens when more than one queue, or no queue at all, matches a routing key

## The taxi company so far

```
website    ─┐
callcenter ─┴─> (default) ─> [ride.requests] ─> manager ─> (default) ─"taxi.t2"─> [taxi.t2] ─> taxi t2
```

The call centre is new. It requests a ride every 5 seconds.

At the moment the manager has to know the name of every taxi queue. In this exercise the manager publishes to
an exchange named after what it does, `taxi.dispatch`, with the taxi id as the routing key. Each taxi decides
which queue receives its rides by binding that queue to the exchange.

## Background

A **direct exchange** delivers a message to every queue that has a binding whose key is equal to the
message's routing key. If several queues are bound with the same key, each one gets a copy. If no binding
matches, the message is dropped. The publisher isn't told about it, at least not yet (see exercise 09).

```python
channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
channel.queue_bind(queue="taxi.t1", exchange="taxi.dispatch", routing_key="t1")
```

Publishing to an exchange that doesn't exist is an error, and the broker closes the channel with
`404 NOT_FOUND`.

## Run it

```shell
cluster/cluster.sh reset
cd 01-direct
python run.py
```

## Tasks

 1. In `taxi.py`, declare a durable direct exchange named `taxi.dispatch` and bind the taxi queue to it
    with the taxi id as the binding key
 2. In `manager.py`, publish to `taxi.dispatch` with the taxi id as the routing key. The manager should declare
    the exchange as well. Why?
 3. Run the scenario, then open the `taxi.dispatch` exchange in the management UI and look at its bindings
 4. In the management UI, create a queue named `t1.inspection` and bind it to `taxi.dispatch` with the
    routing key `t1`. Run the scenario again. Which queues receive the rides for `t1`?
 5. Run `python run.py ghost-taxi`. The manager believes there's a taxi `t9`. Where do the rides for `t9` go?
    Compare the "Publish (In)" and "Publish (Out)" rates of `taxi.dispatch` in the UI

## Check

The taxis log the same lines as before, but `taxi.dispatch` is now listed on the **Exchanges** tab and each
taxi queue has two bindings: one to the default exchange and one to `taxi.dispatch`.

## Questions

 * Steps 4 and 5 used nothing but bindings to change who receives a ride. Which service had to change?
 * Before exercise 01, could the manager have sent the same ride to two taxi queues? With how many publishes?
 * Delete the `taxi.dispatch` exchange in the UI while everything is running. What happens to the manager?
   What happens to the bindings?

## Hints

<details>
<summary>Manager</summary>

```python
channel.exchange_declare(exchange="taxi.dispatch", exchange_type="direct", durable=True)
...
ch.basic_publish(exchange="taxi.dispatch", routing_key=taxi_id, body=body)
```
</details>

## Stretch goals

 * Bind the queues of `t1` and `t2` a second time with the binding key `north`, and those of `t3` and `t4`
   with `south`. Make the manager send a "rush hour" message to all the north taxis with one publish

The solution is in `02-fanout`.
