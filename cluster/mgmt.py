"""Manage the workshop broker through the RabbitMQ management HTTP API. Called by cluster.sh.

The broker is the one the services use: RABBITMQ_URL from the environment, else from broker.env at the root of the
repository, else the local cluster. Each amqp://HOST:PORT URL has its management API at http://HOST:PORT+10000
(5672 -> 15672), and each amqps://HOST URL at https://HOST, unless RABBITMQ_MGMT_URL says otherwise. The URLs are
tried in order, so a stopped local node doesn't break the commands.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

DEFAULT_URL = ",".join(f"amqp://guest:guest@localhost:{port}/%2F" for port in (5672, 5673, 5674))
BROKER_ENV = Path(__file__).resolve().parent.parent / "broker.env"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def setting(name):
    """A setting from the environment, else from broker.env."""
    value = os.environ.get(name)
    if not value and BROKER_ENV.exists():
        for line in BROKER_ENV.read_text().splitlines():
            key, _, val = line.partition("=")
            if key.strip() == name:
                value = val.strip()
    return value


def broker_urls():
    url = setting("RABBITMQ_URL") or DEFAULT_URL
    return [u.strip() for u in url.split(",") if u.strip()]


def is_local():
    """True when every URL points to this machine: the local Docker cluster."""
    return all(urlsplit(u).hostname in LOCAL_HOSTS for u in broker_urls())


class Broker:
    def __init__(self):
        url = urlsplit(broker_urls()[0])
        self.user = unquote(url.username or "guest")
        self.password = unquote(url.password or "guest")
        self.vhost = unquote(url.path[1:]) if len(url.path) > 1 else "/"
        if setting("RABBITMQ_MGMT_URL"):
            apis = [setting("RABBITMQ_MGMT_URL").rstrip("/")]
        else:
            apis = []
            for amqp in map(urlsplit, broker_urls()):
                if amqp.scheme == "amqps":
                    apis.append(f"https://{amqp.hostname}")
                else:
                    apis.append(f"http://{amqp.hostname}:{(amqp.port or 5672) + 10000}")
        self.apis = [api if api.endswith("/api") else api + "/api" for api in dict.fromkeys(apis)]
        self.api = self.apis[0]

    def request(self, method, path, body=None):
        """Send a request to the management API and return the decoded JSON reply, or None."""
        data = json.dumps(body).encode() if body is not None else None
        token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        for api in [self.api] + [a for a in self.apis if a != self.api]:
            req = urllib.request.Request(api + path, data=data, method=method)
            req.add_header("Authorization", f"Basic {token}")
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=15) as reply:
                    content = reply.read()
            except urllib.error.HTTPError as e:
                try:
                    reason = json.loads(e.read()).get("reason", "")
                except ValueError:
                    reason = ""
                raise ApiError(e.code, f"{method} {path}: HTTP {e.code} {reason}".rstrip()) from None
            except (urllib.error.URLError, OSError):
                continue  # this node is down or unreachable, try the next one
            self.api = api
            return json.loads(content) if content else None
        sys.exit(f"Can't reach the management API at {', '.join(self.apis)}\n"
                 f"Check RABBITMQ_URL (or RABBITMQ_MGMT_URL) in broker.env, and that the broker is running.")

    def path(self, collection, name=None):
        """An API path such as /queues/%2F/ride.audit, with the vhost and the name URL-encoded."""
        parts = [collection, quote(self.vhost, safe="")] + ([quote(name, safe="")] if name is not None else [])
        return "/" + "/".join(parts)


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def table(rows):
    """Print rows as left-aligned columns separated by two spaces."""
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)).rstrip())


def reset(broker):
    """Remove everything the exercises create, so that the next one starts from an empty broker."""
    if is_local():
        # The local cluster is ours: recreate the virtual host, as `rabbitmqctl delete_vhost` and `add_vhost` would.
        broker.request("DELETE", "/vhosts/" + quote(broker.vhost, safe=""))
        broker.request("PUT", "/vhosts/" + quote(broker.vhost, safe=""), {})
        broker.request("PUT", broker.path("permissions", broker.user), {"configure": ".*", "write": ".*", "read": ".*"})
        print(f"Virtual host {broker.vhost} has been reset")
        return
    # Another broker, such as CloudAMQP: users can't recreate their virtual host, and the provider adds policies of
    # its own (with negative priorities) and operator policies. Keep those, delete the rest.
    for queue in broker.request("GET", broker.path("queues") + "?columns=name") or []:
        broker.request("DELETE", broker.path("queues", queue["name"]))
    for exchange in broker.request("GET", broker.path("exchanges") + "?columns=name") or []:
        if exchange["name"] and not exchange["name"].startswith("amq."):
            broker.request("DELETE", broker.path("exchanges", exchange["name"]))
    kept = []
    for policy in broker.request("GET", broker.path("policies")) or []:
        if policy["priority"] >= 0:
            broker.request("DELETE", broker.path("policies", policy["name"]))
        else:
            kept.append(policy["name"])
    print(f"Virtual host {broker.vhost} has been reset: queues, exchanges and policies deleted")
    if kept:
        print(f"Kept the broker's own policies (negative priority) and any operator policies: {', '.join(kept)}")


def status(broker):
    overview = broker.request("GET", "/overview")
    print(f"Management API: {broker.api}")
    print(f"Virtual host:   {broker.vhost}")
    print(f"Cluster:        {overview.get('cluster_name')}")
    print(f"RabbitMQ:       {overview.get('rabbitmq_version')}")
    try:
        nodes = broker.request("GET", "/nodes?columns=name,running")
    except ApiError as e:
        if e.status not in (401, 403):
            raise
        print(f"Nodes:          not visible to user {broker.user} (needs the monitoring tag)")
        return
    print()
    table([("node", "running")] + [(n["name"], n.get("running", False)) for n in nodes])


def queues(broker):
    # The message counts come from statistics that the broker refreshes every few seconds.
    columns = "name,type,state,node,leader,members,messages"
    rows = [("name", "type", "state", "leader", "members", "messages")]
    for q in broker.request("GET", broker.path("queues") + f"?columns={columns}") or []:
        leader = q.get("leader") or q.get("node", "")
        members = q.get("members") or [q.get("node", "")]
        messages = q.get("messages")
        rows.append((q["name"], q.get("type", ""), q.get("state", ""), leader, "[" + ", ".join(members) + "]",
                     "?" if messages is None else messages))
    if len(rows) == 1:
        print(f"No queues in virtual host {broker.vhost}")
    else:
        table(rows)


def set_policy(broker, args, collection):
    try:
        definition = json.loads(args.definition)
    except ValueError as e:
        sys.exit(f"The policy definition isn't valid JSON: {e}")
    body = {"pattern": args.pattern, "definition": definition, "apply-to": args.apply_to,
            "priority": args.priority}
    broker.request("PUT", broker.path(collection, args.name), body)
    print(f"Policy {args.name} set on virtual host {broker.vhost}")


def clear_policy(broker, args, collection):
    broker.request("DELETE", broker.path(collection, args.name))
    print(f"Policy {args.name} cleared on virtual host {broker.vhost}")


def list_policies(broker):
    for title, collection in (("policies", "policies"), ("operator policies", "operator-policies")):
        try:
            policies = broker.request("GET", broker.path(collection)) or []
        except ApiError as e:
            if e.status not in (401, 403):
                raise
            continue
        if title == "operator policies" and not policies:
            continue
        print(f"{title}:")
        if not policies:
            print("  none")
            continue
        rows = [("name", "pattern", "apply-to", "definition", "priority")]
        rows += [(p["name"], p["pattern"], p["apply-to"], json.dumps(p["definition"], sort_keys=True, separators=(",", ":")),
                  p["priority"]) for p in policies]
        table(rows)


def main():
    parser = argparse.ArgumentParser(prog="cluster/cluster.sh")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("reset")
    commands.add_parser("status")
    commands.add_parser("queues")
    commands.add_parser("policies")
    commands.add_parser("is-local")
    for command in ("set-policy", "set-operator-policy"):
        sub = commands.add_parser(command)
        sub.add_argument("--apply-to", default="all")
        sub.add_argument("--priority", type=int, default=0)
        sub.add_argument("name")
        sub.add_argument("pattern")
        sub.add_argument("definition")
    for command in ("clear-policy", "clear-operator-policy"):
        commands.add_parser(command).add_argument("name")
    args = parser.parse_args()

    if args.command == "is-local":
        sys.exit(0 if is_local() else 1)
    broker = Broker()
    try:
        if args.command == "reset":
            reset(broker)
        elif args.command == "status":
            status(broker)
        elif args.command == "queues":
            queues(broker)
        elif args.command == "policies":
            list_policies(broker)
        elif args.command in ("set-policy", "set-operator-policy"):
            set_policy(broker, args, "policies" if args.command == "set-policy" else "operator-policies")
        elif args.command in ("clear-policy", "clear-operator-policy"):
            clear_policy(broker, args, "policies" if args.command == "clear-policy" else "operator-policies")
    except ApiError as e:
        hint = ""
        if e.status in (401, 403):
            hint = f"\nUser {broker.user} isn't allowed to do this"
            if "operator" in args.command:
                hint += " (operator policies need the administrator tag)"
        sys.exit(f"{e}{hint}")


if __name__ == "__main__":
    main()
