#!/usr/bin/env bash
# Run a scenario of every exercise against the workshop broker (the local cluster, or the one in broker.env or
# RABBITMQ_URL) and check its output for the lines that the solution to the previous exercise should produce. It
# resets the broker before each exercise and takes about 5 minutes. Usage: tools/smoke.sh [FOLDER...]
set -uo pipefail

cd "$(dirname "$0")/.."
root=$PWD
python=${PYTHON:-$root/.venv/bin/python}
[[ -x $python ]] || python=python3

# folder;run.py arguments;seconds;patterns that must all be found (one per field)
checks=(
  "00-hello-broker;basic;8;\[manager\] ride .* assigning taxi"
  "01-direct;basic;8;\[taxi t[0-9]\] ride .* picking up"
  "02-fanout;basic;8;\[taxi t[0-9]\] ride .* picking up"
  "03-topic;basic;12;\[taxi t[0-9]\] alert: "
  "04-exchange-arguments;audit;12;\[audit\] ride\.(north|south|east)\.;\[manager (north|south)\] ride .* assigning taxi"
  "05-queue-properties;basic;25;handed over to a partner;\[taxi t[0-9]\] alert for (t[0-9]|north|south|sedan|van): "
  "06-quorum-queues;basic;12;ride .*: taxi t[0-9] accepted"
  "07-limits-and-ttl;basic;12;ride\.requests\.north +quorum;taxi\.t1 +quorum"
  "08-policies;--without manager;45;\(expired from ride\.requests;\(maxlen from ride\.requests"
  "09-publisher-confirms;--without manager;45;\(maxlen from ride\.requests;handed over to a partner"
  "10-consumer-acks;basic;12;ride .*: taxi t[0-9] accepted"
  "11-delivery-limits;taxi-on-break;25;rejected from taxi\.t1"
  "12-final;broken-rides;25;has no 'type' .*, rejecting it;rejected from ride\.requests\."
)

failed=0
for check in "${checks[@]}"; do
  IFS=';' read -r folder args seconds patterns <<<"$check"
  if [[ $# -gt 0 && ! " $* " =~ " ${folder%/} " ]]; then continue; fi
  "$root/cluster/cluster.sh" reset >/dev/null
  cd "$root/$folder"
  [[ -x policies.sh ]] && ./policies.sh >/dev/null
  "$python" run.py --for 5 >/dev/null 2>&1
  # shellcheck disable=SC2086
  output=$("$python" run.py $args --for "$seconds" 2>&1; "$root/cluster/cluster.sh" queues)
  cd "$root"
  IFS=';' read -ra wanted <<<"$patterns"
  missing=()
  for pattern in "${wanted[@]}"; do
    grep -Eq -- "$pattern" <<<"$output" || missing+=("$pattern")
  done
  if grep -q Traceback <<<"$output"; then missing+=("no Python traceback"); fi
  if [[ ${#missing[@]} -eq 0 ]]; then
    echo "ok      $folder"
  else
    failed=1
    echo "FAILED  $folder: missing ${missing[*]}"
  fi
done
exit $failed
