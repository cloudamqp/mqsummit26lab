# Exercise 11: poison messages and delivery limits

## What you'll learn

 * What a poison message is, and how it can crash its consumer over and over
 * How quorum queues count failed deliveries and enforce a delivery limit, and which returns don't count
 * How to choose between requeueing and rejecting, how to retry later with delayed retry, and how to make
   dead-lettering itself reliable

## The taxi company so far

The architecture is the same as in exercise 10. Taxis and managers acknowledge their messages, managers take one ride
at a time, and the rides that taxis refuse are dead-lettered to support.

`callcenter.py --broken-every N` makes the call centre send a broken request every Nth ride: the operator forgot to fill
in the vehicle type. The manager can't assign such a ride, and at the moment it crashes on it, before acknowledging it.

From this exercise on, `run.py` restarts a service that crashes after 1 s, as a supervisor such as systemd or Kubernetes
would.

## Background

A **poison message** is one that a consumer can never process. If it makes the consumer crash, the queue delivers it
again to the restarted consumer, which crashes again. With a prefetch limit, the messages behind it wait.

A quorum queue counts the **failed deliveries** of each message: the consumer went away without acknowledging it, or
rejected it with `basic_reject(requeue=True)`. The count is in the `x-delivery-count` header of the message. Once it
goes over the queue's **delivery limit**, the queue stops delivering the message and drops it, or dead-letters it with
the reason `delivery_limit` if the queue has a dead-letter exchange. The default limit is 20. It can be changed with
the `x-delivery-limit` argument or the `delivery-limit` policy key.

Since RabbitMQ 4.3, a message returned with `basic_nack(requeue=True)` doesn't count as a failed delivery: a consumer
can return a message as often as it likes, and the delivery limit never stops it.

A returned message is delivered again straight away. **Delayed retry**, new in RabbitMQ 4.3, makes the queue wait
instead. It's set with the policy keys `delayed-retry-type` (`failed`, `returned`, `all` or `disabled`),
`delayed-retry-min` and `delayed-retry-max`, in milliseconds. With `failed`, a message that failed N times waits
`min × N`, but never more than `max`.

By default, dead-lettering is **at most once**: the queue publishes the dead-lettered message to the dead-letter
exchange and forgets it. If nothing is bound to that exchange, or the target queue is unavailable, the message is lost.
A quorum queue can use `dead-letter-strategy: at-least-once` instead. It keeps the message until the target queue has
confirmed it, and retries in the meantime. This strategy needs `overflow: reject-publish`. With `drop-head`, the queue
falls back to at most once and logs a warning.

## Run it

```shell
cluster/cluster.sh reset
cd 11-delivery-limits
./policies.sh
python run.py --for 5
python run.py broken-rides
```

## Tasks

 1. Run `python run.py broken-rides` and follow one broken ride. How many times is it delivered, and what's its
    delivery count each time? What happens to it in the end? What happens to the rides behind it in the same queue?
 2. In `policies.sh`, add `"delivery-limit": 3` to the `ride-requests` policy and run `./policies.sh` again. Repeat task 1
 3. A ride with a missing field will never succeed, so crashing on it, or returning it to the queue, doesn't help. In
    `manager.py`, reject it with `requeue=False` instead. When would `requeue=True` be the right choice?
 4. A taxi on a break could serve its rides once the break is over. In `taxi.py`, reject them with `requeue=True`, and
    run `python run.py taxi-on-break` for a few seconds. How often does `t1` get the same ride? Then add
    `"delayed-retry-type": "failed"`, `"delayed-retry-min": 2000` and `"delayed-retry-max": 10000` to the `taxis` policy,
    run `./policies.sh` and the scenario again, and look at the times of the `on a break` lines for one ride
 5. Make dead-lettering reliable:
    1. Delete the `ride.dead` queue in the UI, run `python run.py broken-rides --without support` for 20 seconds,
       then start `python support.py`. Are the broken rides there?
    2. Add `"dead-letter-strategy": "at-least-once"` and `"overflow": "reject-publish"` to the `ride-requests` policy,
       run `./policies.sh`, and repeat the experiment. Watch the message count of the ride queues while support is
       away. On CloudAMQP, the queue retries dead-lettering every 3 minutes by default, not every 10 s as on the
       local cluster, so give support time to receive the rides once it's back
 6. Remove `"overflow": "reject-publish"` from the policy, run `./policies.sh`, and look for the warning in the
    broker log: `docker compose -f ../cluster/docker-compose.yml logs | grep at-least-once`. On a CloudAMQP free plan,
    you can't read the broker log: ask the facilitator to show the warning

## Check

```
[callcenter] ride ef986a: the operator forgot to fill in the type
[manager north] ride ef986a has no 'type' (delivery count: 0), rejecting it
[support] sorry Radia, we couldn't serve ride ef986a (rejected from ride.requests.north)
```

```
[taxi t1] ride 32a55a: on a break, returning it for later (redelivered: False)
[taxi t1] ride 32a55a: on a break, returning it for later (redelivered: True)    2 s later
[taxi t1] ride 32a55a: on a break, returning it for later (redelivered: True)    4 s later
```

## Questions

 * Which parts of the company can now lose a ride without anyone being told? Go through the services one by one
 * A taxi crashes on a ride every time, for example because the customer's address breaks its navigation. What stops
   that ride from looping now?
 * In task 4, what would happen if the taxi used `basic_nack(requeue=True)` instead of `basic_reject(requeue=True)`?
   Why do you think RabbitMQ 4.3 treats the two differently?
 * What happens to a ride for a taxi whose break never ends?
 * Why does at-least-once dead-lettering need `reject-publish`?
 * What should support do with the rides it receives, besides apologising?

## Hints

<details>
<summary>Rejecting</summary>

```python
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```
</details>

<details>
<summary>Returning a ride for later</summary>

```python
ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
```
</details>

<details>
<summary>Policies</summary>

```shell
ctl set-policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5,
      "delivery-limit": 3, "dead-letter-strategy": "at-least-once", "overflow": "reject-publish"}'
```

```shell
ctl set-policy --apply-to quorum_queues taxis '^taxi\.' \
    '{"dead-letter-exchange": "rides.dlx", "delayed-retry-type": "failed", "delayed-retry-min": 2000,
      "delayed-retry-max": 10000}'
```
</details>

## Stretch goals

 * Before RabbitMQ 4.3, delayed retries were built with a retry queue. Build one: a `ride.retry` queue with a message
   TTL that dead-letters back to `rides`. Compare it with the `delayed-retry` policy keys

The solution, and the final version of the taxi company, is in `12-final`.
