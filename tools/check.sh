#!/usr/bin/env bash
# Check that everything the workshop needs is ready: Python and pika, and a broker the services can reach. The broker
# is the local Docker cluster, or the one set in broker.env (see the README). Usage: tools/check.sh
set -uo pipefail

cd "$(dirname "$0")/.."
failed=0
# Colours only on a terminal. The Python check below reads the same variables.
if [[ -t 1 ]]; then export OK=$'\033[32mok\033[0m' WARN=$'\033[33mwarn\033[0m' FAIL=$'\033[31mfail\033[0m'
else export OK=ok WARN=warn FAIL=fail; fi
ok()   { printf '  %s    %s\n' "$OK" "$1"; }
warn() { printf '  %s  %s\n' "$WARN" "$1"; }
fail() { printf '  %s  %s\n' "$FAIL" "$1"; failed=1; }
hint() { printf '        %s\n' "$@"; }

# The Python the participant runs the services with: the active virtualenv, else .venv, else python3.
if [[ -n ${VIRTUAL_ENV:-} ]] && command -v python >/dev/null; then
  python=python
elif [[ -x .venv/bin/python ]]; then
  python=.venv/bin/python
else
  python=python3
fi

echo "Python"
if ! command -v "$python" >/dev/null; then
  fail "python3 not found"
  hint "Install Python 3.9 or later"
  echo; echo "Not ready."; exit 1
fi
version=$("$python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
if "$python" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  ok "Python $version ($python)"
else
  fail "Python $version ($python): the workshop needs 3.9 or later"
fi
if [[ $python == python3 ]]; then
  warn "no virtualenv found, using the system python3"
  hint "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi
pika_version=$("$python" -c 'from importlib.metadata import version; print(version("pika"))' 2>/dev/null)
if [[ -z $pika_version ]]; then
  fail "pika is not installed"
  hint "pip install -r requirements.txt"
elif "$python" -c 'import sys; v = tuple(map(int, sys.argv[1].split(".")[:2])); sys.exit(not (1, 3) <= v < (2, 0))' \
    "$pika_version" 2>/dev/null; then
  ok "pika $pika_version"
else
  fail "pika $pika_version: the workshop needs pika 1.3 or later, before 2.0"
  hint "pip install -r requirements.txt"
fi
[[ $failed -eq 0 ]] || { echo; echo "Not ready."; exit 1; }

echo
echo "Broker"
if python3 cluster/mgmt.py is-local; then
  ok "using the local cluster (no broker.env, or broker.env points to localhost)"
  if ! command -v docker >/dev/null; then
    fail "docker not found"
    hint "Install Docker, or use a CloudAMQP instance (see \"Choosing the broker\" in the README)"
  elif ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose v2 not found (\`docker compose version\` fails)"
  elif ! docker info >/dev/null 2>&1; then
    fail "can't talk to the Docker daemon: is it running, and can your user use it?"
  else
    ok "$(docker compose version | head -1)"
  fi
else
  ok "using the broker in broker.env (or RABBITMQ_URL)"
fi

# Connect to every URL, as the services do, and declare a temporary queue to check the permissions too.
"$python" - <<'PY' || failed=1
import os
import socket
import sys
from urllib.parse import urlsplit

sys.path.insert(0, "12-final")
import pika
from common import broker_urls

OK, WARN, FAIL = os.environ["OK"], os.environ["WARN"], os.environ["FAIL"]
urls = broker_urls()
results = []  # (url shown without the password, error or None, fatal)
for url in urls:
    u = urlsplit(url)
    port = u.port or (5671 if u.scheme == "amqps" else 5672)
    shown = f"{u.scheme}://{u.hostname}:{port}{u.path or '/'}"
    try:
        params = pika.URLParameters(url)
        params.connection_attempts = 1
        params.socket_timeout = 5
        params.client_properties = {"connection_name": "workshop-check"}
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        queue = channel.queue_declare(queue="", exclusive=True).method.queue
        channel.queue_delete(queue=queue)
        version = connection._impl.server_properties.get("version", b"?")
        connection.close()
        version = version.decode() if isinstance(version, bytes) else version
        results.append((f"{shown} (RabbitMQ {version})", None, False))
    except pika.exceptions.ProbableAuthenticationError:
        results.append((shown, "wrong user or password", True))
    except pika.exceptions.ProbableAccessDeniedError:
        results.append((shown, "the user can't use this virtual host", True))
    except pika.exceptions.ChannelClosedByBroker as e:
        results.append((shown, f"the broker refused to declare a queue: {e.reply_text}", True))
    except pika.exceptions.AMQPConnectionError as e:
        results.append((shown, f"can't connect {str(e) or ''}".rstrip(), False))
    except socket.gaierror:
        results.append((shown, "host not found", True))
    except Exception as e:
        results.append((shown, f"{type(e).__name__} {e}".rstrip(), True))

reached = sum(error is None for _, error, _ in results)
fatal = any(f for _, _, f in results) or reached == 0
for shown, error, f in results:
    if error is None:
        print(f"  {OK}    AMQP {shown}")
    elif f or reached == 0:
        print(f"  {FAIL}  AMQP {shown}: {error}")
    else:
        print(f"  {WARN}  AMQP {shown}: {error}")
if reached == 0:
    local = all(urlsplit(u).hostname in ("localhost", "127.0.0.1", "::1") for u in urls)
    print("        " + ("Start the local cluster with: cluster/cluster.sh up" if local else
                       "Check RABBITMQ_URL in broker.env, and that the instance is running"))
elif reached < len(urls) and not fatal:
    print(f"        Only {reached} of {len(urls)} nodes are reachable. The services work, but start the others before"
          " the workshop")
sys.exit(1 if fatal else 0)
PY

if status=$(python3 cluster/mgmt.py status 2>&1); then
  ok "management API $(sed -n 's/^Management API: *//p' <<<"$status") (used by cluster/cluster.sh)"
else
  fail "management API: $(head -1 <<<"$status")"
  if grep -q "HTTP 401" <<<"$status"; then
    hint "Wrong user or password, or the user can't use the management API"
  else
    hint "cluster/cluster.sh needs it. Set RABBITMQ_MGMT_URL in broker.env if it isn't at the default address"
  fi
fi

echo
if [[ $failed -eq 0 ]]; then
  echo "Ready for the workshop."
else
  echo "Not ready: fix the failures above and run tools/check.sh again."
  exit 1
fi
