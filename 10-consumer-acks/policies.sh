#!/usr/bin/env bash
# Policies for the taxi company. Run it once after `cluster/cluster.sh reset`, and again after each change.
set -euo pipefail
ctl() { "$(dirname "$0")/../cluster/cluster.sh" "$@"; }

ctl set-policy --apply-to quorum_queues ride-requests '^ride\.requests\.' \
    '{"message-ttl": 30000, "dead-letter-exchange": "rides.dlx", "max-length": 5}'

# TODO(ex10): dead-letter the rides that taxis reject to `rides.dlx`.

ctl set-policy --apply-to exchanges rides '^rides$' '{"alternate-exchange": "rides.unrouted"}'

ctl policies
