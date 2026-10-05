#!/usr/bin/env bash
# Manage the 3-node workshop cluster. Run `cluster/cluster.sh help` for usage.
set -euo pipefail

cd "$(dirname "$0")"
compose() { docker compose "$@"; }
node() { echo "rmq${1:?node number 1-3 required}"; }
ctl() { local n=$1; shift; compose exec -T "$(node "$n")" rabbitmqctl "$@"; }

usage() {
  cat <<USAGE
Usage: cluster/cluster.sh <command>

  up              start the 3 nodes and wait until they are healthy
  down            stop and remove the nodes and all their data
  reset           delete every queue, exchange, binding and policy (keeps the nodes running)
  status          show cluster members and running nodes
  queues          list queues with their type, the node(s) they live on and their message count
  stop-node N     stop node N (1-3), keeping its data
  start-node N    start node N (1-3) again
  ctl N ARGS...   run rabbitmqctl ARGS on node N, e.g. "ctl 1 list_queues name type leader"

Management UI: http://localhost:15672 (also 15673, 15674), user guest, password guest
AMQP ports:    5672 (rmq1), 5673 (rmq2), 5674 (rmq3)
USAGE
}

running_node() {
  for n in 1 2 3; do
    if compose exec -T "$(node "$n")" rabbitmq-diagnostics -q check_running >/dev/null 2>&1; then
      echo "$n"; return
    fi
  done
  echo "No running node found. Start the cluster with: cluster/cluster.sh up" >&2
  exit 1
}

case "${1:-help}" in
  up)         compose up -d --wait ;;
  down)       compose down -v ;;
  reset)
    n=$(running_node)
    ctl "$n" delete_vhost / >/dev/null
    ctl "$n" add_vhost / >/dev/null
    ctl "$n" set_permissions -p / guest '.*' '.*' '.*' >/dev/null
    echo "Virtual host / has been reset" ;;
  status)     ctl "$(running_node)" cluster_status ;;
  queues)     ctl "$(running_node)" list_queues -q name type leader members messages | column -t -s $'\t' ;;
  stop-node)  compose stop "$(node "${2:-}")" ;;
  start-node) compose start "$(node "${2:-}")" && compose up -d --wait "$(node "$2")" ;;
  ctl)        shift; n=${1:?node number required}; shift; ctl "$n" "$@" ;;
  *)          usage ;;
esac
