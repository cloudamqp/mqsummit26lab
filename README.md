# RabbitMQ workshop: the taxi company

A hands-on introduction to RabbitMQ and message brokers. You'll build the
messaging of a small taxi company, in Python with the
[`pika`](https://pika.readthedocs.io/) client, one exercise at a time:

```
website, callcenter ─> ride requests ─> managers ─> taxis
                                ops ─> alerts ─> taxis
```

Each service is a short Python script. They talk to each other only through a RabbitMQ broker: by default a
3-node RabbitMQ `4.2` cluster that runs in Docker on your machine, or a [CloudAMQP](https://www.cloudamqp.com)
instance (see [Choosing the broker](#choosing-the-broker)).

## Prerequisites

 * Python `3.9` or later
 * For the local cluster: Docker with Docker Compose v2 (`docker compose version`), and ports 5672 to 5674 and 15672
   to 15674 free on `localhost`

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Choosing the broker

Without any configuration, everything uses the local cluster. To use another broker, such as a CloudAMQP instance:

```shell
cp broker.env.example broker.env
```

Then set `RABBITMQ_URL` in `broker.env` to the AMQP URL of the broker. For CloudAMQP, copy the URL from the
instance's details page: `amqps://USER:PASSWORD@HOST.rmq.cloudamqp.com/VHOST`. The part after the last `/` is the
virtual host the exercises use. `broker.env` is ignored by git, so your password stays out of the repository.

 * The services (`common.py:connect()`) and `cluster/cluster.sh` both read `broker.env`. A `RABBITMQ_URL`
   environment variable overrides it
 * `RABBITMQ_URL` can hold several URLs separated by commas, one per node. The services try them in random order
 * `cluster/cluster.sh` talks to the broker's management HTTP API, at `https://HOST` for `amqps://` URLs and at
   `http://HOST:15672` for `amqp://` URLs. Set `RABBITMQ_MGMT_URL` if yours is somewhere else

On CloudAMQP, a few tasks need the local cluster instead:

 * Stopping and starting nodes (exercises 05 and 06). `cluster.sh stop-node` only works with the local cluster
 * Operator policies (exercise 08, task 5) need a user with the `administrator` tag
 * Reading the broker log (exercise 11, task 5): use the CloudAMQP console
 * On a single-node instance, quorum queues have one member, so exercise 06 has no leader election to watch

## The broker

```shell
cluster/cluster.sh status      # the broker, its RabbitMQ version and its nodes
cluster/cluster.sh queues      # queues, their type, their nodes and their message count
cluster/cluster.sh reset       # delete every queue, exchange, binding and policy in the virtual host (*)
cluster/cluster.sh policies    # list the policies
cluster/cluster.sh set-policy --apply-to queues NAME PATTERN DEFINITION
cluster/cluster.sh clear-policy NAME
```

These work with any broker. (*) On CloudAMQP, `reset` keeps CloudAMQP's own policies, which have negative
priorities, and its operator policies. The local cluster has a few more commands:

```shell
cluster/cluster.sh up          # start the 3 nodes, rmq1 to rmq3
cluster/cluster.sh stop-node 2 # stop one node, keeping its data
cluster/cluster.sh start-node 2
cluster/cluster.sh ctl 1 list_exchanges name type   # run any rabbitmqctl command on node 1
cluster/cluster.sh down        # stop the cluster and delete all its data
```

 * Management UI: http://localhost:15672 (also on 15673 and 15674), user
   `guest`, password `guest`. On CloudAMQP, open the management UI from the instance's console
 * AMQP: `localhost:5672` (`rmq1`), `localhost:5673` (`rmq2`), `localhost:5674` (`rmq3`)

Reset the broker at the start of each exercise. Most exercises change how
queues or exchanges are declared, and RabbitMQ refuses to declare an existing
queue or exchange with different properties.

## How the exercises work

Each numbered folder is a complete copy of the taxi company:

 * The code in exercise N+1 is the code of exercise N with the tasks of exercise N done. If you get stuck, move on to
   the next folder: everything there works
 * `README.md` explains the topic, lists the tasks and asks a few questions. The places where you need to change the
   code are marked with `TODO(exN)`
 * `tools/diff.sh N` shows the solution to exercise N (with the scaffolding for exercise N+1)
 * Stretch goals aren't part of the solutions

In every folder:

```shell
python run.py                  # start every service of the "basic" scenario
python run.py --list           # list the scenarios
python run.py two-managers     # start another scenario
python run.py --without t3     # leave out the services whose command contains "t3"
python run.py --for 20         # stop after 20 seconds
python taxi.py --id t3         # run one service by hand, in another terminal
```

`Ctrl-C` stops every service that `run.py` started.

## Exercises

 * [`00-hello-broker`](00-hello-broker): connections, channels, queues and the default exchange
 * [`01-direct`](01-direct): exchanges and bindings, the direct exchange
 * [`02-fanout`](02-fanout): the fanout exchange, several bindings per queue, message properties
 * [`03-topic`](03-topic): the topic exchange and binding patterns
 * [`04-exchange-arguments`](04-exchange-arguments): the headers exchange, alternate and internal exchanges (optional)
 * [`05-queue-properties`](05-queue-properties): durable, exclusive and server-named queues, persistent messages,
   node restarts (optional)
 * [`06-quorum-queues`](06-quorum-queues): replicated queues and leader election
 * [`07-limits-and-ttl`](07-limits-and-ttl): length limits, overflow, TTL and dead-lettering
 * [`08-policies`](08-policies): policies and operator policies (optional)
 * [`09-publisher-confirms`](09-publisher-confirms): publisher confirms, the mandatory flag, unroutable messages
 * [`10-consumer-acks`](10-consumer-acks): acknowledgements, rejecting, redelivery and prefetch
 * [`11-delivery-limits`](11-delivery-limits): poison messages, delivery limits, at-least-once dead-lettering
 * [`12-final`](12-final): the final version of the taxi company

## Troubleshooting

 * `PRECONDITION_FAILED - inequivalent arg ...`: a queue or exchange already exists with different properties. Run
   `cluster/cluster.sh reset`
 * `NOT_FOUND - no exchange ...`: a service publishes to an exchange that nobody has declared yet. Check the order in
   which the services declare things, or start the service that declares it first
 * A service keeps logging `connection lost`: check that the broker is running with `cluster/cluster.sh status`,
   and that `RABBITMQ_URL` in `broker.env` is right
