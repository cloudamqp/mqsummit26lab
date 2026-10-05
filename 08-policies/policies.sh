#!/usr/bin/env bash
# Policies for the taxi company. Run it once after `cluster/cluster.sh reset`, and again after each change.
set -euo pipefail
ctl() { "$(dirname "$0")/../cluster/cluster.sh" ctl 1 "$@"; }

# TODO(ex08): a policy for the `ride.requests.<zone>` queues with the arguments removed from `manager.py`.

# TODO(ex08): a policy for the `rides` exchange with its alternate exchange.

ctl list_policies -q | column -t -s $'\t'
