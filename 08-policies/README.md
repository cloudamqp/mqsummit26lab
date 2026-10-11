# Exercise 08: policies

This exercise is optional.

## What you'll learn

 * How to configure queues and exchanges from the broker side with policies, instead of hard-coding arguments
 * How a policy matches queues or exchanges by name, and what happens when several policies match
 * What operator policies are, and how the broker combines a policy with queue arguments

## The taxi company so far

The architecture is the same as in exercise 07, and the call centre's ride requests now expire after 10 seconds.

In exercise 07, the TTL, the length limit and the dead-letter exchange were written into `manager.py`. To change any
of them, every manager had to be updated, the queues deleted, and everything restarted. The same applied to the
alternate exchange of `rides` in exercise 04.

## Background

A **policy** is a set of settings stored in the broker. It applies to every queue or exchange whose name matches
a regular expression, including the ones that already exist and the ones declared later. Changing or deleting a
policy takes effect immediately, without restarting anything. `cluster/cluster.sh set-policy` sets one through
the management HTTP API. On the local cluster, `rabbitmqctl set_policy` takes the same arguments.

```shell
cluster/cluster.sh set-policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5}'
```

 * Policy keys are the argument names without the `x-` prefix: `message-ttl`, `max-length`, `overflow`,
   `dead-letter-exchange`, `alternate-exchange` and so on
 * `--apply-to` restricts a policy to `queues`, `classic_queues`, `quorum_queues`, `streams`, `exchanges` or `all`
 * Only one policy applies to a given queue or exchange: the matching one with the highest `--priority`.
   The definitions of several policies are never merged
 * An **operator policy** (`set-operator-policy`) is a second kind of policy, meant for the people who run the
   broker. It's applied on top of the regular policy, and for numeric limits such as `max-length` the lower value wins
 * When a queue has both an argument and a policy for the same setting, the broker decides which one wins. For
   numeric limits, such as `max-length` or `message-ttl`, it's the lower value

The queue type can't be set by a policy, so `x-queue-type` stays in the code.

## Run it

```shell
cluster/cluster.sh reset
cd 08-policies
./policies.sh
python run.py
```

## Tasks

 1. In `policies.sh`, add a policy named `ride-requests` for the `ride.requests.<zone>` quorum queues, with the
    TTL, the maximum length and the dead-letter exchange from exercise 07. Remove those arguments from `manager.py`
 2. In `policies.sh`, add a policy named `rides` for the `rides` exchange with its alternate exchange. Remove the
    argument from `common.py`
 3. Reset the broker, run `./policies.sh` and then the scenario. In the UI, check the **Policy** and
    **Effective policy definition** of a ride queue. Check that the east rides still reach the partner, as in
    exercise 04: `python run.py --for 30 | grep east`
 4. With the scenario running, change the maximum length to 3 and run `./policies.sh` again. Did you need to
    restart anything?
 5. Add an operator policy that limits every queue to 1000 messages. Look at the effective policy definition of
    `ride.requests.north` again
 6. Add a second policy that matches `ride.requests.north` only, with a higher priority and only
    `{"max-length": 10}`. What happens to the TTL of `ride.requests.north`?
 7. Bring back `"x-max-length": 2` in `manager.py` (reset the broker first). Which limit applies now, the
    argument or the policy?

## Check

```
$ ./policies.sh
...
policies:
name           pattern            apply-to       definition                                                               priority
ride-requests  ^ride\.requests\.  quorum_queues  {"dead-letter-exchange":"rides.dlx","max-length":5,"message-ttl":30000}  0
rides          ^rides$            exchanges      {"alternate-exchange":"rides.unrouted"}                                  0
```

## Questions

 * Which settings belong in the application code, and which in policies? Who should own each?
 * Why does `rides` need the pattern `^rides$`, not just `rides`?
 * In task 6, the TTL disappeared from `ride.requests.north`. How would you add a north-only setting without
   losing the others?

## Hints

<details>
<summary>policies.sh</summary>

```shell
ctl set-policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5}'
ctl set-policy --apply-to exchanges rides '^rides$' '{"alternate-exchange": "rides.unrouted"}'
```

```shell
ctl set-operator-policy --apply-to queues limits '.*' '{"max-length": 1000}'
```
</details>

## Stretch goals

 * Set the same policies with `curl` and the HTTP API that `cluster.sh` uses. On the local cluster:
   `curl -u guest:guest -X PUT http://localhost:15672/api/policies/%2F/ride-requests -H 'content-type: application/json' -d '...'`
 * Export the broker definitions from the UI (**Overview**, **Export definitions**) and find your policies in the file

The solution is in `09-publisher-confirms`.
