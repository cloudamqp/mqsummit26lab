# Exercise 06: quorum queues

## What you'll learn

 * How a quorum queue keeps a copy of its messages on several nodes, and stays available when one node stops
 * How to pick the queue type when declaring a queue, and why an existing queue can't change its type
 * Which features quorum queues don't support, and why

## The taxi company so far

The architecture doesn't change. Every queue so far has been a **classic queue**. A classic queue lives on one
node, and in exercise 05 you saw what happens when that node stops: the queue is unavailable, and rides published
to it are lost until the node comes back.

The rides and the taxi queues are too important for that. In this exercise they become quorum queues.

`run_service()` in `common.py` now reconnects. When a service loses its connection, for example because its node
stopped, it logs `connection lost`, waits 2 seconds and runs its `main()` again. `connect()` tries the nodes in random
order, so the new connection goes to a node that's still running. Running `main()` again also declares the service's
queues, exchanges and bindings again, and starts its consumers again.

## Background

A **quorum queue** is replicated with the [Raft](https://raft.github.io/) consensus algorithm. By default it has
a member on 3 nodes. One member is the **leader**, which handles publishes and deliveries, and the others are
**followers**. A message is confirmed only once a majority of members have written it to disk. If the leader's
node stops, the remaining members elect a new leader, as long as a majority of them is still running.

The queue type is chosen with the `x-queue-type` argument:

```python
channel.queue_declare(queue="ride.requests.north", durable=True, arguments={"x-queue-type": "quorum"})
```

Quorum queues are always durable and they store every message on disk, persistent or not. They can't be
exclusive or auto-delete, so they don't suit short-lived queues such as the manager's reply queue.

A queue's type is fixed when the queue is created. Declaring an existing classic queue with
`x-queue-type: quorum` fails with `406 PRECONDITION_FAILED`.

## Run it

```shell
cluster/cluster.sh reset
cd 06-quorum-queues
python run.py
```

## Tasks

 1. In `manager.py` and `taxi.py`, make `ride.requests.<zone>` and `taxi.<id>` quorum queues
 2. Run the scenario without resetting the broker first. What happens, and why? Reset and run it again
 3. Run `../cluster/cluster.sh queues`. Where are the members of each queue? Which node is the leader of
    `ride.requests.north`?
 4. With the scenario running, stop the leader's node with `../cluster/cluster.sh stop-node N`. Watch the logs:
    which services reconnect? Is any ride lost? Run `../cluster/cluster.sh queues` to find the new leader
 5. Repeat task 4 with the node that holds `ride.unassigned`, which is still a classic queue. Compare
 6. Start the node again. Does the leader move back?
 7. Stop two nodes. What happens to the quorum queues now? Start them again before moving on

## Check

```
$ ../cluster/cluster.sh queues
name                 type    state    leader       members                                  messages
ride.requests.north  quorum  running  rabbit@rmq2  [rabbit@rmq1, rabbit@rmq2, rabbit@rmq3]  0
taxi.t1              quorum  running  rabbit@rmq3  [rabbit@rmq1, rabbit@rmq2, rabbit@rmq3]  0
...
```

## Questions

 * A service connected to `rmq1` consumes from a queue whose leader is on `rmq2`. Does that work? What does it cost?
 * In `common.py`, `connect()` tries the nodes in random order. Why random, and not always `rmq1` first?
 * A quorum queue with 3 members tolerates one node failure. How many failures does a queue with 5 members tolerate?
   Would a queue with 4 members be any better than one with 3?
 * Why can't the manager's reply queue be a quorum queue?

## Hints

<details>
<summary>Declaring a quorum queue</summary>

```python
channel.queue_declare(queue=queue, durable=True, arguments={"x-queue-type": "quorum"})
```
</details>

## Stretch goals

 * Try to declare an exclusive quorum queue. What does the broker answer?
 * Look at the **Queues and Streams** tab while a node is down: what does it show for each member?

The solution is in `07-limits-and-ttl`.
