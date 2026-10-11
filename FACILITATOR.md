# Facilitator notes

Expected observations and answers for each exercise. Statements about broker behaviour were checked against the
RabbitMQ source at tag `v4.2.9` (the version in the `rabbitmq:4.2-management` image used by `cluster/`), and most of
them were also reproduced on the workshop cluster. Paths are relative to the
[`rabbitmq-server`](https://github.com/rabbitmq/rabbitmq-server/tree/v4.2.9) repository.

## Before the workshop

 * Pull the image ahead of time: `docker pull rabbitmq:4.2-management`
 * Ask participants to run `tools/check.sh` before the workshop. It checks Python, `pika`, Docker (local cluster
   only) and that the broker is reachable over AMQP and through the management API
 * Run `tools/smoke.sh` after changing any exercise. It resets the broker, runs a scenario of every folder and checks the
   log for the lines that the previous exercise's solution produces. It takes about 5 minutes
 * The cluster sets `dead_letter_worker_publisher_confirm_timeout` to 10 s in `cluster/advanced.config`. The default is
   180 s (`deps/rabbit/Makefile:120`). It's how often a quorum queue retries at-least-once dead-lettering when the
   target can't be reached (`deps/rabbit/src/rabbit_fifo_dlx_worker.erl:362-366`), and 180 s is too long for
   exercise 11
 * Every queue in the exercises is durable from the start, because transient non-exclusive queues are a deprecated
   feature in 4.x (`deps/rabbit/src/rabbit_amqqueue.erl:117`)
 * `cluster/cluster.sh` uses the management HTTP API (`deps/rabbitmq_management/src/rabbit_mgmt_dispatcher.erl:107-155`)
   so that it also works with CloudAMQP. The message counts that `queues` shows come from statistics refreshed every
   5 s by default (`collect_statistics_interval`, `deps/rabbit/Makefile:42`), so they can lag a little. `/api/nodes`
   needs the `monitoring` tag (`deps/rabbitmq_management/src/rabbit_mgmt_wm_nodes.erl:35-36`) and operator policies
   the `administrator` tag (`deps/rabbitmq_management/src/rabbit_mgmt_wm_operator_policy.erl:74-79`)

### Running the workshop on CloudAMQP

Participants use free CloudAMQP plans and set `RABBITMQ_URL` in `broker.env` (see the README). A free plan has a
single node, and participants can't stop or start it or read its logs. Things that differ from the local cluster:

 * Demo on the local cluster, on the projector: exercise 05 tasks 5 and 6 (node restart, persistent messages) and
   exercise 06 tasks 3 to 7 (members, leader election, losing quorum). `stop-node` and `start-node` refuse to run
   against a remote broker
 * Every quorum queue has one member on a single-node instance
 * Exercise 08 task 5: operator policies need the `administrator` tag, which free-plan users don't have (verified:
   `HTTP 401 Not administrator user`)
 * Exercise 11: `cluster/advanced.config` isn't applied, so at-least-once dead-lettering retries every 180 s by default
   (also in 4.3.6, `deps/rabbit/Makefile:117` at `v4.3.6`) instead of 10 s. Show the task 5 warning from the local
   cluster's log
 * The instance's RabbitMQ version may not be the `4.2.9` that these notes were checked against
 * `cluster/cluster.sh reset` empties the virtual host instead of recreating it, because CloudAMQP users can't create
   virtual hosts. It deletes the queues, the exchanges and the policies with priority 0 or more, and keeps CloudAMQP's
   own policies (`default`, `Celery`, `stream-limits` and `tmp`, with negative priorities) and its operator policy.
   The workshop's policies have priority 0, so they replace CloudAMQP's on the queues they match

Suggested timing for a full day: 00 to 03 in the morning, 06, 07, 09, 10 and 11 in the afternoon. Exercises 04, 05 and
08 are optional.

## 00: hello, broker

 * Task 1: the taxis don't consume from any queue yet, so `taxi.py` logs "going home" and exits
 * Task 2: 2 connections, the manager's and the website's, because the taxis leave straight away. Once the taxis
   consume, there are 6, spread across the nodes because `connect()` shuffles them. Each has one channel
 * Two channels: with pika's `BlockingConnection`, publishing from the consumer callback on the same channel is fine.
   It's still worth mentioning that flow control blocks a whole connection, which is why separate connections for
   publishing and consuming are a common recommendation
 * A ride to `taxi.t9`: the default exchange routes by queue name and there's no such queue, so the ride is dropped
   without any error
 * Who declares: both sides, because `queue_declare` is idempotent. If the manager publishes before a taxi has declared
   its queue, those rides are lost
 * Stretch, two managers: the queue delivers the requests round-robin between the two consumers

## 01: direct exchange

 * Task 4: `t1.inspection` and `taxi.t1` both get a copy of the rides for `t1`. Nothing changed in any service
 * Task 5: the rides for `t9` match no binding and are dropped. The channel counts them as unroutable
   (`deps/rabbit/src/rabbit_channel.erl:2257-2264`)
 * Before 01, sending one ride to two taxis took two publishes and the manager had to know both queue names
 * Deleting `taxi.dispatch`: its bindings are deleted with it. The manager's next publish fails with `404 NOT_FOUND`,
   which closes the channel, and the manager crashes. The taxis keep consuming but receive no rides until they
   restart and bind again

## 02: fanout exchange

 * The routing key is ignored, so with `t1` every taxi still gets the alert
 * Task 5: if `taxi.t3` exists (a previous run declared it), it keeps collecting alerts while `t3` is away, and `t3`
   gets them all when it comes back. After a reset, `t3` has never declared its queue, so its alerts are dropped
 * With the direct exchange, ops would publish once per taxi and would need the list of taxis. A new taxi only needs
   to bind its queue to `taxi.alerts`

## 03: topic exchange

 * Task 4: nothing publishes to `ride.requests` any more
 * Task 5: the rides in `east` only reach the audit service. Without it, they match no binding and are dropped
 * Task 6: the south manager's queue is durable, so the south rides wait for it
 * `taxi.dispatch` as a topic exchange: bind with the exact taxi id. `taxi.alerts`: bind with `#`
 * `#` matches every routing key. `ride.*` matches two-word keys such as `ride.north` but not `ride.north.van`

## 04: headers exchange and exchange arguments

 * Task 4: declaring `rides` again with a new argument fails with `406 PRECONDITION_FAILED` (`inequivalent arg
   'alternate-exchange'`). The broker closes the channel and the services crash. Reset and run again
 * Task 6: the audit binding `ride.#` matches the rides in `east`, so `rides` has a destination for them and never uses
   its alternate exchange. The alternate exchange is used only when an exchange routes a message to no destination at
   all (`deps/rabbit/src/rabbit_exchange.erl:416-423`)
 * Task 7: publishing to an internal exchange fails with `403 ACCESS_REFUSED` (`cannot publish to internal exchange`,
   `deps/rabbit/src/rabbit_channel.erl:976-979`)
 * North vans only: one `x-match: any` binding can't do it, because a message with `zone: north, type: van` also matches
   the north sedans through `zone`. Possible answers are a header that names the group, such as `group: north-van`,
   with a matching binding per taxi, or a second headers exchange with `x-match: all` bindings
 * The headers exchange can address every taxi with an extra binding header that every taxi has, such as `fleet: all`.
   Then `taxi.alerts` isn't needed any more
 * Stretch, exchange-to-exchange binding: a destination exchange counts as a destination even if it routes the message
   nowhere, so it disables the alternate exchange in the same way as the audit queue
   (`deps/rabbit/src/rabbit_exchange.erl:399-414`)

## 05: queue properties and persistent messages

 * Reply queues are named `amq.gen-...` and flagged exclusive. They're deleted when the manager's connection closes,
   and a restarted manager gets a new name. A reply sent to the old name is dropped
 * Task 5, verified: with the website publishing every 2 s (persistent) and the call centre every 5 s (transient),
   only the website's rides are left after the node restart. While the node is down, `cluster/cluster.sh queues` shows
   the queue in state `stopped`, with `?` messages
 * Task 6, verified: declaring the classic queue while its node is down fails with `404 NOT_FOUND` (`queue
   'ride.requests.north' in vhost '/' process is stopped by supervisor`, `deps/rabbit/src/rabbit_amqqueue.erl:670-685`),
   so the north manager crashes. The north rides published meanwhile are lost, persistent or not: the queue was empty
   after the node came back
 * Every manager in a zone shares the request queue to share the work, but replies have to go back to the manager that
   sent the ride

## 06: quorum queues

 * Task 2: declaring an existing classic queue with `x-queue-type: quorum` fails with `406 PRECONDITION_FAILED`
   (`inequivalent arg 'x-queue-type'`)
 * Task 4, verified: services connected to the stopped node log `CONNECTION_FORCED` and reconnect to another node
   within a few seconds. The quorum queues whose leader was on that node elect a new one, and no stored ride is lost
 * Task 5: `ride.unassigned` is unavailable while its node is down, and the rides in `east` are lost meanwhile
 * Task 6: the leader doesn't move back. `rabbitmq-queues rebalance quorum` redistributes leaders
 * Task 7: with two of three nodes down, the quorum queues have no majority and can't accept or deliver messages
 * Consuming through a node other than the leader's works. The messages travel between nodes, which costs some
   latency and inter-node traffic
 * 5 members tolerate 2 failures. 4 members tolerate 1, like 3, because a majority of 4 is 3
 * A quorum queue can't be exclusive, auto-delete or non-durable (`deps/rabbit/src/rabbit_quorum_queue.erl:251-256`).
   Stretch, verified: a named exclusive quorum queue fails with `406 PRECONDITION_FAILED - invalid property
   'exclusive-owner'`, and a server-named one (`queue=""`) with `Cannot declare a server-named queue for type
   rabbit_quorum_queue`

## 07: length limits, TTL and dead-lettering

 * Task 3, verified: with no managers, support reports both `maxlen` (dropped from the head of a full queue) and
   `expired` rides
 * Task 4: a quorum queue only checks the TTL of the message at its head (`deps/rabbit/src/rabbit_fifo.erl:2250-2263`).
   A call-centre ride behind a website ride with a 30 s TTL is dead-lettered when it reaches the head, not after 10 s
 * Task 5: with `reject-publish`, refused rides are not dead-lettered. Without confirms the website isn't told
 * Task 6: the manager consumes with `auto_ack=True`, which has no prefetch limit, so the broker pushes every waiting
   ride to it at once. The rides wait in the manager's process, where no TTL or length limit applies. Exercise 10
   fixes this
 * Ride requests suit `drop-head`: the oldest request is the least useful. Payments suit `reject-publish` with
   confirms, so that the publisher can retry and nothing is dropped silently

## 08: policies

 * How a quorum queue combines an argument and a policy (`deps/rabbit/src/rabbit_quorum_queue.erl:346-356`,
   `deps/rabbit/src/rabbit_queue_type_util.erl:20-28`): `max-length`, `max-length-bytes`, `message-ttl` and `expires`
   take the lower value, `overflow` takes the policy, and `dead-letter-exchange` takes the queue argument
   (`deps/rabbit/src/rabbit_quorum_queue.erl:1708-1713`)
 * Task 4: the new limit applies straight away, without a restart
 * Task 5: the effective definition contains the keys of both policies. For a key in both, the broker merges the two
   values: the lower one for numeric limits, and the operator policy's value for `overflow`
   (`deps/rabbit/src/rabbit_policy.erl:78-93`, `deps/rabbit/src/rabbit_policies.erl:211-237`)
 * Task 6: only the policy with the highest priority applies, and definitions aren't merged, so the north queue loses
   its TTL and dead-lettering. The north-only policy has to repeat every key
 * Task 7: the lower of the argument (2) and the policy (5) applies
 * Pattern: a policy pattern is an unanchored regular expression. `rides` would also match `rides.dlx` and
   `rides.unrouted`

## 09: publisher confirms and the mandatory flag

The completed table, verified on the workshop cluster:

 * No options: the ride goes to the partner with the alternate exchange, and is dropped without it. The website isn't
   told either way
 * `--mandatory`: with the alternate exchange, the ride is routed, so nothing is returned. Without it, the broker returns
   the ride with `NO_ROUTE` and the return callback logs it
 * `--confirms`: the broker acks the ride in both cases. An unroutable message is confirmed straight away
   (`deps/rabbit/src/rabbit_channel.erl:2270-2272`)
 * `--confirms --mandatory`: routed and acked with the alternate exchange. Without it, `basic_publish()` raises
   `UnroutableError`. The return is sent before the confirm (`deps/rabbit/src/rabbit_channel.erl:2205-2207`)

Other points:

 * Task 3, verified: without confirms the website logs every ride as requested, and the rides refused by the full
   queue are lost. With confirms it raises `NackError`. The queue can hold one message more than `max-length`, because a
   quorum queue only refuses new messages once it's over the limit (`deps/rabbit/src/rabbit_fifo.erl:2579-2585`)
 * A confirm per publish costs a round trip. To go faster, publish a batch and then wait for all its confirms, or use
   an asynchronous connection that handles confirms in a callback
 * The call centre can lose rides that are unroutable, refused by a full queue, or in flight when its connection drops

## 10: consumer acknowledgements and prefetch

 * Task 1, verified: with `auto_ack=True` the ride is gone when the taxi breaks down. With manual acknowledgements the
   ride stays in `taxi.t1` and is delivered again with `redelivered: True` when the taxi restarts
 * Task 3, verified: with `requeue=True` the ride loops between the queue and the taxi, 21 deliveries in total, and is
   then dropped: the default delivery limit of a quorum queue is 20
   (`deps/rabbit/src/rabbit_quorum_queue.erl:131`, checked in `deps/rabbit/src/rabbit_fifo.erl:1944-1960`)
 * Task 4: with `requeue=False` and no dead-letter exchange the ride is dropped. With the `taxis` policy, support gets
   it with the reason `rejected`
 * Task 5, verified: with `auto_ack=True` the broker still alternates between the two managers, so the slow one gets as
   many rides as the fast one. Its rides wait in its process, and the queue shows nothing ready or unacknowledged.
   With a prefetch of 1, the fast manager takes most rides and the backlog stays in the queue
 * Crash between reply and ack: the ride is delivered again, so the manager may get two replies for it. Acknowledging
   first means a crash loses the ride instead. Redelivery means consumers have to cope with duplicates
 * A fast consumer can use a prefetch in the hundreds. A consumer that takes seconds per message should use 1
 * Stretch, consumer timeout: the broker closes the channel with `PRECONDITION_FAILED` (`delivery acknowledgement on
   channel ... timed out`, `deps/rabbit/src/rabbit_channel.erl:2888-2902`), and the channel's unacknowledged messages
   go back to the queue. Since only one policy applies, `consumer-timeout` has to go into the same `taxis` policy

## 11: poison messages and delivery limits

 * Task 1, verified: the broken ride is delivered 21 times, with `x-delivery-count` going from 0 to 20, then
   dead-lettered with the reason `delivery_limit`. A returned message is delivered before the other messages in the
   queue (`deps/rabbit/src/rabbit_fifo.erl:2132-2139`), so with a prefetch of 1 the rides behind it wait
 * Task 2: with `delivery-limit: 3` the ride is delivered 4 times
 * Every return increments the count, including returns after a consumer crash
   (`deps/rabbit/src/rabbit_fifo.erl:3097-3112`), so the limit also stops a ride that crashes its consumer every time
 * `requeue=True` suits failures that can go away, such as a database that's briefly unavailable, ideally with a delay
 * Task 4, verified: with the default at-most-once strategy and no `ride.dead` queue, the dead-lettered rides are lost.
   With `at-least-once`, they stay counted in the source queue and reach support once it declares `ride.dead` again,
   within the 10 s retry interval of the workshop cluster
 * Task 5: the broker logs `Falling back to dead-letter-strategy at-most-once ... incompatible with effective overflow
   strategy drop-head` (`deps/rabbit/src/rabbit_quorum_queue.erl:1726-1735`). Messages waiting to be dead-lettered
   count towards the length limit (`deps/rabbit/src/rabbit_fifo.erl:2579-2585`), so with `drop-head` a full queue
   would have to drop them
