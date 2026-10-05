# Exercise 09: publisher confirms and the mandatory flag

## What you'll learn

 * That by default a publisher doesn't know whether the broker routed, stored or dropped its message
 * How publisher confirms tell the publisher that the broker has taken responsibility for a message, or refused it
 * How the mandatory flag makes the broker return messages that can't be routed to any queue

## The taxi company so far

The architecture is the same as in exercise 08. The settings of the ride queues and of `rides` now live in
`policies.sh`.

Several times now, rides have disappeared without anyone being told: the rides for a zone nobody serves before
exercise 04, the rides published while a classic queue's node was down in exercise 05, and the rides refused by a
full queue in exercise 07. In each case the website logged "ride requested" and the customer waited for a taxi that
never came.

## Background

**Publisher confirms** are turned on per channel. After that, the broker acknowledges every message the channel
publishes:

 * `basic.ack` when the broker has taken responsibility for the message: it's been routed and every queue it was
   routed to has accepted it. For a quorum queue, that means a majority of its members have written it to disk.
   A message that wasn't routed to any queue is acked straight away
 * `basic.nack` when a queue refused the message, for example a full queue with `overflow: reject-publish`

The **mandatory flag** is set per message. If a mandatory message can't be routed to any queue, the broker sends it
back to the publisher with `basic.return` (reply text `NO_ROUTE`), before the confirm.

With `pika`'s `BlockingChannel`, after `channel.confirm_delivery()`:

 * `basic_publish()` waits for the confirm
 * it raises `pika.exceptions.UnroutableError` when a mandatory message is returned
 * it raises `pika.exceptions.NackError` when the broker nacks the message

Without confirms, returned messages go to the callback registered with `channel.add_on_return_callback()`.

## Run it

```shell
cluster/cluster.sh reset
cd 09-publisher-confirms
./policies.sh
python run.py
```

`website.py` now has two options, `--confirms` and `--mandatory`, that do nothing yet.

## Tasks

 1. In `website.py`, implement `--confirms` and `--mandatory`:
    1. With `--confirms`, call `channel.confirm_delivery()`. Without it, register a return callback that logs the
       rides the broker sends back
    2. Publish with `mandatory=args.mandatory`
    3. Catch `UnroutableError` and `NackError` and tell the customer what happened. Log "ride requested" only when
       the ride was accepted
 2. Run the company without the website (`python run.py --without website`) and run the website by hand in a second
    terminal with each combination of options. Fill in the table below, first with the policies as they are, then
    without the alternate exchange (`../cluster/cluster.sh ctl 1 clear_policy rides`)

    | `website.py` options        | east ride, alternate exchange | east ride, no alternate exchange |
    |-----------------------------|-------------------------------|----------------------------------|
    | (none)                      |                               |                                  |
    | `--mandatory`               |                               |                                  |
    | `--confirms`                |                               |                                  |
    | `--confirms --mandatory`    |                               |                                  |

 3. Make the ride queues refuse rides when they're full, then stop the scenario and run only the website, with and
    without `--confirms`. What does the customer see in each case? Compare the number of messages in the queue with
    the limit

    ```shell
    ../cluster/cluster.sh ctl 1 set_policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
        '{"max-length": 3, "overflow": "reject-publish", "dead-letter-exchange": "rides.dlx"}'
    ```
 4. Run `./policies.sh` again to restore the policies

## Check

```
[website] ride 4e1c1d: sorry Radia, we don't serve east
[website] ride 5e60e0: sorry Grace, we're too busy, try again later
```

## Questions

 * With the alternate exchange in place, the mandatory flag made no difference. Why?
 * A ride published with `--confirms` but without `--mandatory` to a zone nobody serves: is it acked or nacked? Why
   does that make sense?
 * `basic_publish()` now waits for every confirm before the next ride. What does that cost? How would you publish
   many messages quickly and still use confirms?
 * The call centre still publishes without confirms. Which of its rides can be lost without anyone noticing?

## Hints

<details>
<summary>Confirms and returns</summary>

```python
if args.confirms:
    channel.confirm_delivery()
else:
    channel.add_on_return_callback(lambda ch, method, properties, body: log.warning(
        "ride %s returned by the broker: %s", decode(body)["ride_id"], method.reply_text))
```
</details>

<details>
<summary>Publishing</summary>

```python
try:
    channel.basic_publish(exchange="rides", routing_key=..., body=..., properties=properties,
                          mandatory=args.mandatory)
    log.info("ride %s requested ...", ...)
except UnroutableError:
    log.warning("ride %s: sorry %s, we don't serve %s", ...)
except NackError:
    log.warning("ride %s: sorry %s, we're too busy, try again later", ...)
```
</details>

## Stretch goals

 * Retry a nacked ride up to 3 times, a second apart, before telling the customer
 * Stop the node that holds the leader of `ride.requests.north` while the website publishes with `--confirms`.
   Is any ride lost?

The solution is in `10-consumer-acks`.
