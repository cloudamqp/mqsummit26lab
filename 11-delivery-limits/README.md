# Exercise 11: poison messages and delivery limits

## What you'll learn

 * What a poison message is, and why returning a failed message to its queue can loop forever
 * How quorum queues count deliveries and enforce a delivery limit
 * How to choose between requeueing and rejecting, and how to make dead-lettering itself reliable

## The taxi company so far

The architecture is the same as in exercise 10. Taxis and managers acknowledge their messages, managers take one ride
at a time, and the rides that taxis refuse are dead-lettered to support.

`callcenter.py --broken-every N` makes the call centre send a broken request every Nth ride: the operator forgot to fill
in the vehicle type. The manager can't assign such a ride. At the moment it logs an error and returns the ride to the
queue with `basic_nack(requeue=True)`, hoping that it'll work next time.

## Background

A **poison message** is one that a consumer can never process. If the consumer returns it to the queue each time, the
queue delivers it again and again. That uses the consumer's time, and with a prefetch limit it can block the messages
behind it.

A quorum queue counts how many times each message has been delivered and returned. The count is in the
`x-delivery-count` header of the message. Once it goes over the queue's **delivery limit**, the queue stops returning
the message and drops it, or dead-letters it with the reason `delivery_limit` if the queue has a dead-letter exchange.
The default limit is 20. It can be changed with the `x-delivery-limit` argument or the `delivery-limit` policy key.

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

 1. Run `python run.py broken-rides` and follow one broken ride. How many times is it delivered? What happens to it in
    the end? What happens to the rides behind it in the same queue while it loops?
 2. In `policies.sh`, add `"delivery-limit": 3` to the `ride-requests` policy and run `./policies.sh` again. Repeat task 1
 3. A ride with a missing field will never succeed, so returning it to the queue doesn't help. In `manager.py`, reject
    it with `requeue=False` instead. When would `requeue=True` be the right choice?
 4. Make dead-lettering reliable:
    1. Delete the `ride.dead` queue in the UI, run `python run.py broken-rides --without support` for 20 seconds,
       then start `python support.py`. Are the broken rides there?
    2. Add `"dead-letter-strategy": "at-least-once"` and `"overflow": "reject-publish"` to the `ride-requests` policy,
       run `./policies.sh`, and repeat the experiment. Watch the message count of the ride queues while support is
       away
 5. Remove `"overflow": "reject-publish"` from the policy, run `./policies.sh`, and look for the warning in the
    broker log: `docker compose -f ../cluster/docker-compose.yml logs | grep at-least-once`

## Check

```
[callcenter] ride ef986a: the operator forgot to fill in the type
[manager north] ride ef986a has no 'type' (delivery count: 0), rejecting it
[support] sorry Radia, we couldn't serve ride ef986a (rejected from ride.requests.north)
```

## Questions

 * Which parts of the company can now lose a ride without anyone being told? Go through the services one by one
 * A taxi crashes on a ride every time, for example because the customer's address breaks its navigation. What stops
   that ride from looping now?
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
<summary>Policy</summary>

```shell
ctl set_policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5,
      "delivery-limit": 3, "dead-letter-strategy": "at-least-once", "overflow": "reject-publish"}'
```
</details>

## Stretch goals

 * Rides that fail for a temporary reason should be retried later, not straight away. Build a delayed retry with a
   `ride.retry` queue that has a message TTL and dead-letters back to `rides`

The solution, and the final version of the taxi company, is in `12-final`.
