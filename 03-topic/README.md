# Exercise 03: topic exchange

## What you'll learn

 * How a topic exchange matches dotted routing keys against binding patterns with `*` and `#`
 * How consumers choose what they receive by picking a binding pattern, without the publisher knowing about them
 * How several consumers can receive the same message, each through its own queue and pattern

## The taxi company so far

The company has grown. The city is split into zones, and the fleet has two types of vehicle, sedans and vans.
`common.py` now gives each taxi in `FLEET` a zone and a type, and each ride a zone and the type the customer wants.
The manager only assigns a ride to a taxi of the same zone and type.

There's now one manager per zone, plus an audit service that records every ride. The website and call centre
shouldn't need to know how many managers there are, or which zone each one covers.

```
website    ─┐                       "ride.north.*" ─> [ride.requests.north] ─> manager north
callcenter ─┴─> (rides, topic) ─────"ride.south.*" ─> [ride.requests.south] ─> manager south
                                    "ride.#"       ─> [ride.audit]          ─> audit

manager ─> (taxi.dispatch, direct) ─> [taxi.<id>] ─> taxi
ops     ─> (taxi.alerts, fanout)   ─> [taxi.<id>] ─> taxi
```

Customers can now request rides in the `east` zone, but the company has no taxis there yet.

## Background

A **topic exchange** routes on routing keys made of words separated by dots, such as `ride.north.van`. A binding
key is a pattern:

 * `*` matches exactly one word: `ride.north.*` matches `ride.north.van` and `ride.north.sedan`
 * `#` matches zero or more words: `ride.#` matches every key that starts with `ride`

Like a direct exchange, a topic exchange delivers one copy to each matching queue. A queue with two matching
bindings still gets the message only once.

## Run it

```shell
cluster/cluster.sh reset
cd 03-topic
python run.py
```

## Tasks

 1. In `website.py` and `callcenter.py`, declare the durable topic exchange `rides` and publish each ride to it
    with the routing key `ride.<zone>.<type>`, for example `ride.north.van`
 2. In `manager.py`, declare `rides` and bind the manager's queue to it so that it receives every ride in its
    zone
 3. In `audit.py`, bind `ride.audit` so that it receives every ride
 4. Run the scenario. Then look at the old `ride.requests` queue in the UI. Is anything still publishing to it?
    Delete it
 5. Some customers request rides in `east`. Which services see these rides? Which don't?
 6. Run the scenario without the south manager (`python run.py --without south`). After a while, start it
    by hand with `python manager.py --zone south`. What happens to the south rides requested while it was away?

## Check

```
[website] ride 51c0de requested by Ada in north (van)
[audit] ride.north.van: ride 51c0de for Ada from website
[manager north] ride 51c0de from website: assigning taxi t2
[taxi t2] ride 51c0de: picking up Ada in north
[audit] ride.east.sedan: ride 77e1b4 for Ken from callcenter
```

## Questions

 * Could a topic exchange do the job of `taxi.dispatch`? Of `taxi.alerts`? What binding keys would you use?
 * What does the binding `#` match? And `ride.*`?
 * Rides in `east` reach only the audit service. If the audit service didn't exist, what would happen to them?
   Exercise 04 deals with this

## Hints

<details>
<summary>Binding patterns</summary>

```python
channel.queue_bind(queue=queue, exchange="rides", routing_key=f"ride.{args.zone}.*")
channel.queue_bind(queue="ride.audit", exchange="rides", routing_key="ride.#")
```
</details>

## Stretch goals

 * The company buys vans that take van rides in any zone. Add a `--binding` option to `manager.py` and start
   a manager with `python manager.py --zone vans --binding 'ride.*.van'`

The solution is in `04-exchange-arguments`.
