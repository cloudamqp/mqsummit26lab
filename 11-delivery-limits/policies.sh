#!/usr/bin/env bash
# Policies for the taxi company. Run it once after `cluster/cluster.sh reset`, and again after each change.
set -euo pipefail
ctl() { "$(dirname "$0")/../cluster/cluster.sh" "$@"; }

# TODO(ex11): dead-letter a ride request after 3 deliveries, and make sure dead-lettered rides aren't lost.
ctl set-policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5}'

# TODO(ex11): when a taxi returns a ride, deliver it again after a delay that grows with each attempt.
ctl set-policy --apply-to quorum_queues taxis '^taxi\.' '{"dead-letter-exchange": "rides.dlx"}'

ctl set-policy --apply-to exchanges rides '^rides$' '{"alternate-exchange": "rides.unrouted"}'

ctl policies
