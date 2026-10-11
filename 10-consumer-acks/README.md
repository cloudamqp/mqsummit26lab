# Exercise 10: consumer acknowledgements and prefetch

## What you'll learn

 * The difference between automatic and manual acknowledgements, and what each one risks
 * How the broker redelivers the messages of a consumer that goes away without acknowledging them
 * How a consumer can reject a message, with or without sending it back to the queue
 * How the prefetch limit (`basic_qos`) controls how many unacknowledged messages a consumer holds

## The taxi company so far

The architecture is the same as in exercise 09. `website.py` uses confirms and the mandatory flag when asked to.

Every consumer so far has used `auto_ack=True`. The broker considers a message delivered as soon as it has sent it,
whether or not the consumer has done anything with it.

Two new options help to see what that means. `taxi.py --crash-every N` makes a taxi break down on every Nth ride,
before it has picked up the customer. `taxi.py --on-break` makes a taxi refuse every ride.

## Background

With **manual acknowledgements** (`auto_ack=False`), the consumer tells the broker what happened to each message:

 * `basic_ack(delivery_tag)`: done, the broker can forget the message
 * `basic_nack(delivery_tag, requeue=True)` or `basic_reject(delivery_tag, requeue=True)`: put it back in the queue
   for another delivery
 * `basic_nack` or `basic_reject` with `requeue=False`: drop the message, or dead-letter it if the queue has a
   dead-letter exchange. The death reason is `rejected`

`basic_nack` can also reject several messages at once with `multiple=True`.

If a consumer's channel or connection closes, every message it hadn't acknowledged goes back to the queue. The next
delivery of such a message has `method.redelivered` set to `True`.

The **prefetch limit** set with `channel.basic_qos(prefetch_count=N)` is the maximum number of unacknowledged messages
the broker sends to a consumer. It only applies to manual acknowledgements. With `auto_ack=True` there's no limit:
the broker sends messages as fast as the consumer's connection takes them.

## Run it

```shell
cluster/cluster.sh reset
cd 10-consumer-acks
./policies.sh
python run.py --for 5
python run.py crashing-taxi
```

## Tasks

 1. Run `python run.py crashing-taxi`. Taxi `t1` breaks down on its second ride. Run `../cluster/cluster.sh queues`:
    is the ride still in `taxi.t1`? Start the taxi again with `python taxi.py --id t1`. Does it get the ride?
 2. In `taxi.py`, use manual acknowledgements: acknowledge each alert, and each ride once the reply has been sent.
    Repeat task 1
 3. In `taxi.py`, when the taxi is on a break, reject the ride with `requeue=True`, and run
    `python run.py taxi-on-break`. What happens? Does it ever stop? Count the deliveries
 4. Change it to `requeue=False`. Where does the ride go now? Add a policy for the taxi queues to `policies.sh` so that
    rejected rides go to `rides.dlx` and support can apologise
 5. Run `python run.py two-managers`: one manager takes 4 seconds per ride, the other half a second. Look at
    `ride.requests.north` in the UI (the **Ready** and **Unacked** columns), and count the rides each manager assigns
 6. In `manager.py`, use manual acknowledgements with a prefetch limit of 1. Repeat task 5
 7. Go back to exercise 07, task 6. Why did the queue stay empty although the manager was slow?

## Check

```
[taxi t1] ride 778944: the taxi broke down
[runner] taxi.py --id t1 --crash-every 2 exited with code 1
...
[taxi t1] ride 778944: picking up Ken in north (redelivered: True)
```

```
[taxi t1] ride 25feb6: on a break, refusing it (redelivered: False)
[support] sorry Donald, we couldn't serve ride 25feb6 (rejected from taxi.t1)
```

## Questions

 * The taxi acknowledges a ride after sending its reply. What happens if it crashes between the two? Would the
   other order be better?
 * With `auto_ack=True`, where were the rides waiting in task 5? What happens to them if the slow manager crashes?
 * What's a sensible prefetch limit for a consumer that takes 1 ms per message? And 10 seconds?
 * In task 3, the loop stopped by itself after a while. Why? Exercise 11 answers this

## Hints

<details>
<summary>Manual acknowledgements</summary>

```python
channel.basic_consume(queue=queue, on_message_callback=on_message)  # auto_ack defaults to False
...
ch.basic_ack(delivery_tag=method.delivery_tag)
ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
```
</details>

<details>
<summary>Prefetch</summary>

```python
channel.basic_qos(prefetch_count=1)
```
</details>

<details>
<summary>Taxi policy</summary>

```shell
ctl set-policy --apply-to quorum_queues taxis '^taxi\.' '{"dead-letter-exchange": "rides.dlx"}'
```
</details>

## Stretch goals

 * Acknowledge the rides in batches with `basic_ack(delivery_tag, multiple=True)`. When is that worth it?
 * Set a consumer timeout policy (`"consumer-timeout": 10000`) on the taxi queues, and make a taxi take longer than
   that to acknowledge. What does the broker do?

The solution is in `11-delivery-limits`.
