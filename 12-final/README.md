# 12: the taxi company, final version

This folder has the solution to exercise 11. It's the complete taxi company, with every part built during the workshop.

## Architecture

```
website ────┐
callcenter ─┴─> (rides, topic) ─"ride.<zone>.*"─> [ride.requests.<zone>] ─> manager <zone>
                   ├─"ride.#"─> [ride.audit] ─> audit                       (audit scenario only)
                   └─(alternate exchange)─> (rides.unrouted, internal) ─> [ride.unassigned] ─> partner

manager ─> (taxi.dispatch, direct) ─"<id>"─┐
ops ─────> (taxi.alerts, fanout) ──────────┼─> [taxi.<id>] ─> taxi <id>
ops ─────> (taxi.notices, headers) ────────┘

taxi ─> (default) ─"amq.gen-..."─> [amq.gen-..., exclusive] ─> manager     (replies)

[ride.requests.<zone>], [taxi.<id>] ─(expired, rejected, delivery limit)─> (rides.dlx, fanout) ─> [ride.dead] ─> support
```

## What each part uses

 * `website.py`: a topic exchange, persistent messages, publisher confirms and the mandatory flag
 * `callcenter.py`: per-message TTL, and broken requests on demand
 * `manager.py`: a quorum queue per zone, manual acknowledgements with a prefetch of 1, an exclusive server-named
   reply queue, rejecting poison messages
 * `taxi.py`: a quorum queue bound to a direct, a fanout and a headers exchange, manual acknowledgements, rejecting
   rides, replies with `reply_to`
 * `ops.py`: fanout and headers exchanges
 * `partner.py`: an internal exchange used as an alternate exchange
 * `support.py`: dead-lettering and its headers
 * `audit.py`: a catch-all topic binding
 * `policies.sh`: TTL, length limit, overflow, dead-lettering, delivery limit and the alternate exchange, all as
   policies

## Run it

```shell
cluster/cluster.sh reset
cd 12-final
./policies.sh
python run.py --list
python run.py
```

## Where to go next

These topics weren't covered:

 * [Streams](https://www.rabbitmq.com/docs/streams), for example to replay every ride requested today
 * [Shovels](https://www.rabbitmq.com/docs/shovel) and [federation](https://www.rabbitmq.com/docs/federation), to move
   rides between the brokers of two cities
 * [Single active consumer](https://www.rabbitmq.com/docs/consumers#single-active-consumer), to keep the rides of a
   zone in order with several managers on standby
 * [AMQP 1.0](https://www.rabbitmq.com/docs/amqp), the other protocol that RabbitMQ 4 supports natively
