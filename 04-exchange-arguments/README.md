# Exercise 04: headers exchange and exchange arguments

This exercise is optional.

## What you'll learn

 * How a headers exchange routes on message headers instead of the routing key, with `x-match` set to `any` or `all`
 * How the `alternate-exchange` argument catches messages that would otherwise be dropped
 * What internal exchanges are, and why an exchange's arguments can't be changed by declaring it again

## The taxi company so far

```
website    ─┐                       "ride.north.*" ─> [ride.requests.north] ─> manager north
callcenter ─┴─> (rides, topic) ─────"ride.south.*" ─> [ride.requests.south] ─> manager south
                   │ nothing matches "ride.east.*"
                   └──(alternate exchange)──> (rides.unrouted, fanout, internal) ─> [ride.unassigned] ─> partner

ops ─> (taxi.alerts, fanout)                    ─> every taxi
ops ─> (taxi.notices, headers) {"zone": "north"} ─> taxis t1, t2
```

Two things are new:

 * A partner company has agreed to take the rides in zones the company doesn't serve. `partner.py` consumes them
   from `ride.unassigned`
 * Ops wants to send an alert to one taxi, or to the taxis in one zone, or of one type, not only to every taxi.
   `ops.py` already picks a target and sets the headers. A message for the north zone has the header
   `zone: north`, and a message for `t3` has `id: t3`

Every service that declares `rides` now calls `declare_rides()` in `common.py`, so its arguments are in one place.

## Background

A **headers exchange** ignores the routing key. Each binding has a table of arguments: the special argument
`x-match` and a set of header names and values. With `x-match: all`, a message matches if it has every header in
the binding with the same value. With `x-match: any`, one matching header is enough.

Exchanges, like queues, take **optional arguments** when they're declared. The best-known one is
`alternate-exchange`. When a message published to an exchange matches no binding at all, the exchange passes it
to its alternate exchange instead of dropping it.

An **internal** exchange (`internal=True`) can't be published to by clients. Messages only reach it from another
exchange, for example as an alternate exchange or through an exchange-to-exchange binding.

Declaring an exchange that already exists with different arguments fails with `406 PRECONDITION_FAILED`, and the
broker closes the channel. To change the arguments, you have to delete the exchange first. Exercise 08 shows a
better way.

## Run it

```shell
cluster/cluster.sh reset
cd 04-exchange-arguments
python run.py
```

## Tasks

 1. In `taxi.py`, declare the durable headers exchange `taxi.notices` and bind the taxi queue to it with a binding
    that matches `id`, `zone` or `type`
 2. In `ops.py`, publish the targeted alerts to `taxi.notices`. Then run the company without ops
    (`python run.py --without ops`), and run ops by hand in another terminal with `python ops.py --to van --interval 3`.
    Only `t2` and `t4`, the vans, should log `alert for van`. Try `--to north` and `--to t3` too
 3. In `partner.py`, declare `rides.unrouted` as a durable, internal fanout exchange and bind `ride.unassigned`
    to it
 4. In `common.py`, add the `alternate-exchange` argument to `rides`. Run the scenario without resetting the
    broker first. What happens? Why? Reset the broker and try again
 5. Check that the partner receives the rides in `east`: in the output of `python run.py --for 30 | grep east`,
    every `requested ... in east` line should be followed by a `[partner] ride ... handed over` line for the same
    ride id
 6. Run `python run.py audit`. Does the partner still get the rides in `east`? Why not?
 7. Try publishing straight to `rides.unrouted` from the UI (**Exchanges**, `rides.unrouted`, **Publish message**),
    or from Python. What happens?

## Check

```
[ops] alert for north: Heavy rain from 18:00
[taxi t1] alert for north: Heavy rain from 18:00
[taxi t2] alert for north: Heavy rain from 18:00
[website] ride 2c1e08 requested by Joe in east (sedan)
[partner] ride 2c1e08 in east handed over to a partner company
```

## Questions

 * Ops wants to reach the vans in the north zone only, and no other taxi. Can one binding per taxi with
   `x-match: any` do that? What could?
 * The headers exchange can send an alert to all taxis too. How? Do we still need `taxi.alerts`?
 * In task 6 a binding was added somewhere else, and the partner stopped getting the rides. What does this
   tell you about when the alternate exchange is used?
 * Why is it useful that `rides.unrouted` is internal?

## Hints

<details>
<summary>Headers binding</summary>

```python
taxi = FLEET[args.id]
channel.exchange_declare(exchange="taxi.notices", exchange_type="headers", durable=True)
channel.queue_bind(queue=queue, exchange="taxi.notices",
                   arguments={"x-match": "any", "id": args.id, "zone": taxi["zone"], "type": taxi["type"]})
```
</details>

<details>
<summary>Alternate exchange</summary>

```python
channel.exchange_declare(exchange="rides", exchange_type="topic", durable=True,
                         arguments={"alternate-exchange": "rides.unrouted"})
```

```python
channel.exchange_declare(exchange="rides.unrouted", exchange_type="fanout", durable=True, internal=True)
```
</details>

## Stretch goals

 * Bind a new exchange to `rides` with `channel.exchange_bind()`, then bind a queue to the new exchange. This is
   an exchange-to-exchange binding. Does it affect the alternate exchange like the audit queue did?

The solution is in `05-queue-properties`.
