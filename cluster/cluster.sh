#!/usr/bin/env bash
# Manage the workshop broker: the local 3-node cluster, or the broker set in broker.env (for example a CloudAMQP
# instance). Run `cluster/cluster.sh help` for usage.
set -euo pipefail

cd "$(dirname "$0")"
compose() { docker compose "$@"; }
node() { echo "rmq${1:?node number 1-3 required}"; }
ctl() { local n=$1; shift; compose exec -T "$(node "$n")" rabbitmqctl "$@"; }
mgmt() { python3 mgmt.py "$@"; }

usage() {
  cat <<USAGE
Usage: cluster/cluster.sh <command>

Any broker (the one set in broker.env, or the local cluster):
  status          show the broker, its RabbitMQ version and its nodes
  queues          list queues with their type, the node(s) they live on and their message count
  reset           delete every queue, exchange and policy in the virtual host
  policies        list the policies and operator policies
  set-policy [--apply-to X] [--priority N] NAME PATTERN DEFINITION
  clear-policy NAME
  set-operator-policy [--apply-to X] [--priority N] NAME PATTERN DEFINITION
  clear-operator-policy NAME

Local cluster only (Docker):
  up              start the 3 nodes and wait until they are healthy
  down            stop and remove the nodes and all their data
  stop-node N     stop node N (1-3), keeping its data
  start-node N    start node N (1-3) again
  ctl N ARGS...   run rabbitmqctl ARGS on node N, e.g. "ctl 1 list_queues name type leader"

Local cluster: management UI http://localhost:15672 (also 15673, 15674), user guest, password guest
               AMQP ports 5672 (rmq1), 5673 (rmq2), 5674 (rmq3)
USAGE
}

local_only() {
  if ! mgmt is-local; then
    echo "$1 needs the local Docker cluster, but broker.env (or RABBITMQ_URL) points to another broker." >&2
    case $1 in
      stop-node|start-node) echo "A CloudAMQP free plan has a single node that can't be stopped: follow this task on the facilitator's screen." >&2 ;;
      *) echo "To use the local cluster for this command: RABBITMQ_URL=amqp://guest:guest@localhost cluster/cluster.sh $*" >&2 ;;
    esac
    exit 1
  fi
}

case "${1:-help}" in
  status|queues|reset|policies|set-policy|clear-policy|set-operator-policy|clear-operator-policy) mgmt "$@" ;;
  up)         local_only "$@"; compose up -d --wait ;;
  down)       local_only "$@"; compose down -v ;;
  stop-node)  local_only "$@"; compose stop "$(node "${2:-}")" ;;
  start-node) local_only "$@"; compose start "$(node "${2:-}")" && compose up -d --wait "$(node "$2")" ;;
  ctl)        local_only "$@"; shift; n=${1:?node number required}; shift; ctl "$n" "$@" ;;
  *)          usage ;;
esac
