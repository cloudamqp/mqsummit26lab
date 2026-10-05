# Exercise 07: length limits, TTL and dead-lettering

## What you'll learn

 * How to limit the length of a queue, and the two things the broker can do when it's full: drop the oldest
   message, or refuse new ones
 * How to make messages expire with a per-queue or a per-message time to live (TTL)
 * How dead-lettering sends dropped and expired messages to another exchange instead of discarding them

## The taxi company so far

```
website, callcenter ─> (rides) ─> [ride.requests.<zone>] ─> manager ─> (taxi.dispatch) ─> [taxi.<id>] ─> taxi
                                         │ expired or dropped (once you've done this exercise)
                                         └──> (rides.dlx, fanout) ─> [ride.dead] ─> support
```

`support.py` is new. It consumes from `ride.dead` and apologises to the customers whose rides couldn't be served.
`manager.py` has a new option, `--slow`, that makes it take longer to assign each ride.

A ride request that has waited for minutes isn't useful any more: the customer has found another taxi. A queue
of requests that grows without limit while the managers are away only makes things worse when they're back.

## Background

Queue arguments that limit what a queue holds:

 * `x-max-length`: the maximum number of messages. `x-max-length-bytes` does the same for the total size of the
   message bodies
 * `x-overflow`: what happens when the queue is full. `drop-head` (the default) drops the oldest message, and
   `reject-publish` refuses the new one
 * `x-message-ttl`: the number of milliseconds a message can stay in the queue

A publisher can also give one message a TTL with the `expiration` property, a string with a number of
milliseconds. When both are set, the lower value wins.

A message that's dropped from the head, that expires, or that a consumer rejects (exercise 10) is
**dead-lettered** if the queue has the `x-dead-letter-exchange` argument. It's republished to that exchange,
with headers such as `x-first-death-reason` (`expired`, `maxlen`, `rejected`...) and `x-first-death-queue`.

Like the queue type, the arguments of an existing queue can't be changed by declaring it again.

## Run it

```shell
cluster/cluster.sh reset
cd 07-limits-and-ttl
python run.py
```

## Tasks

 1. In `manager.py`, give `ride.requests.<zone>` a TTL of 30 seconds, a maximum length of 5 messages, and the
    dead-letter exchange `rides.dlx`
 2. In `callcenter.py`, give each ride a TTL of 10 seconds
 3. Reset the broker and run `python run.py --for 5`, so that every queue is declared. Then run the company without
    managers: `python run.py --without manager`. Watch `ride.requests.north` in the UI and the support logs.
    Which rides are dead-lettered, and why?
 4. Look closely at the timing of the `expired` messages from the call centre. Are they dead-lettered exactly
    10 seconds after they're published?
 5. Change the overflow behaviour to `reject-publish` and repeat task 3. What happens to the rides when the
    queue is full? Does the website notice?
 6. Run `python run.py --without manager` for a while, then start a slow manager by hand:
    `python manager.py --zone north --slow 5`. Watch the queue in the UI. Is the manager really keeping up?
    Keep this in mind for exercise 10

## Check

```
[support] sorry Grace, we couldn't serve ride be3cdf (expired from ride.requests.south)
[support] sorry Tim, we couldn't serve ride 68507f (maxlen from ride.requests.south)
```

## Questions

 * Which is better for ride requests, `drop-head` or `reject-publish`? And for a queue of payments?
 * In task 5, a full queue refused rides and nobody was told. How could the website find out? Exercise 09 answers this
 * To change the TTL from 30 to 60 seconds, you have to delete the queue and declare it again. Every manager has to
   be updated and restarted too. Is there a better way? Exercise 08 answers this

## Hints

<details>
<summary>Queue arguments</summary>

```python
channel.queue_declare(queue=queue, durable=True, arguments={
    "x-queue-type": "quorum",
    "x-message-ttl": 30_000,
    "x-dead-letter-exchange": "rides.dlx",
    "x-max-length": 5,
})
```
</details>

<details>
<summary>Per-message TTL</summary>

```python
properties = pika.BasicProperties(expiration="10000")
```
</details>

## Stretch goals

 * Use `x-dead-letter-routing-key` to dead-letter the rides with a routing key of your choice, and route them
   differently in `rides.dlx`
 * Give each taxi queue a TTL for alerts only. Can you? Why not?

The solution is in `08-policies`.
