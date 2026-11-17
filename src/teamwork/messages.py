"""The agent-to-agent mailbox: queued, prioritised, preemptible messages.

Why this exists: ``Inbox.md`` is prose a human reads. An agent that needs another
agent to do something had no way to say so except the board, so a request either
became a task (losing the "do this before that" intent) or was shouted into a
worklog nobody reads. This module is the channel: a message is a record with a
priority, it is delivered when the recipient next runs, and an ``urgent`` one
preempts the recipient's current assignment through the supervisor.

The contract, in the order an agent meets it:

* **send** - ``M-nnnn`` from one instance to another with a priority
  (``urgent`` > ``high`` > ``normal`` > ``low``), a subject, an optional body,
  an optional task it concerns, and an optional message it answers;
* **queue** - the recipient's lane packet opens with its pending messages in
  priority order, so it sees them without polling, and ``message inbox`` is the
  same list on demand (a long lane can re-check between steps);
* **claim** - ``message take`` marks one in progress, so a second lane of the same
  role does not process it twice; ``message done`` closes it with the result;
* **preempt** - an ``urgent`` message makes the recipient's live lane stoppable:
  the supervisor pauses the task (status ``paused``, the message id recorded),
  runs the urgent work, and resumes the paused task afterwards.

Addressing is one problem with four faces. A **bare instance** name reaches one
lane in this team; ``role:<r>`` reaches every instance of a role; ``*`` reaches
the whole roster. All three are *local*: they fan out at send time into the
per-instance store under ``Runtime/Mailbox/<Instance>/``. ``team:<Name>`` and
``session:<id>`` name something this tree cannot see - another team's tree or
another ``pi`` session - so they land on the **bus**: ``$TEAMWORK_BUS`` or
``<repo>/.pi/Teamwork/Bus``, one directory per address key, the same JSON shape
plus ``scope``, ``sender_session`` and ``expires``. A local inbox reads its own
mailbox and the bus keys it answers to, merged in one priority order.

State is one JSON file per message, mutated under a lock. Nothing here is a
second ledger: the ledger records that a message was sent, taken and done; the
mailbox holds the message itself.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .config import DIR_RUNTIME
from .io import atomic_write, lock
from .names import pascal, safe_component

DIR_MAILBOX = "Mailbox"
DIR_BUS = "Bus"
BUS_ENV = "TEAMWORK_BUS"
BUS_PATH = (".pi", "Teamwork", DIR_BUS)
PRIORITIES = ("urgent", "high", "normal", "low")
PRIORITY_RANK = {name: index for index, name in enumerate(PRIORITIES)}
STATES = ("pending", "taken", "done", "dropped")
SCOPES = ("instance", "role", "team", "session", "all")
BUS_SCOPES = ("team", "session")
SUBJECT_MAX = 120
BODY_MAX = 4000
INBOX_LINES = 8


def mailbox_dir(root: Path) -> Path:
    return root / DIR_RUNTIME / DIR_MAILBOX


def instance_dir(root: Path, instance: str) -> Path:
    return mailbox_dir(root) / instance


def mailbox_lock(root: Path) -> Path:
    return root / DIR_RUNTIME / "Locks" / "mailbox.lock"


def bus_root(root: Path) -> Path:
    """Where a non-local address lands: ``$TEAMWORK_BUS`` or ``<repo>/.pi/Teamwork/Bus``."""
    override = os.environ.get(BUS_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return root.joinpath(*BUS_PATH)


def bus_lock(root: Path) -> Path:
    return bus_root(root) / ".lock"


def bus_key(scope: str, value: str) -> str:
    """The directory one bus address owns; ``session:<id>`` -> ``session-<id>``."""
    return safe_component(f"{scope}-{value}")


def bus_dir(root: Path, address: str) -> Path:
    scope, value = parse_address(address)
    return bus_root(root) / bus_key(scope, value)


def parse_address(text: str) -> tuple:
    """``('*'|'role:x'|'team:x'|'session:x'|'instance')`` -> ``(scope, value)``."""
    raw = str(text).strip()
    if raw == "*":
        return ("all", "*")
    for scope in BUS_SCOPES + ("role",):
        prefix = f"{scope}:"
        if raw.startswith(prefix):
            value = raw[len(prefix) :].strip()
            if not value:
                raise ValueError(f"{scope}: needs a name after the colon")
            return (scope, value)
    if ":" in raw:
        raise ValueError(f"unknown address '{raw}': use *, role:<r>, team:<Name> or session:<id>")
    if not raw:
        raise ValueError("a message needs a recipient")
    return ("instance", raw)


def role_of(instance: str) -> str:
    """``Developer-2`` -> ``developer``; an instance is ``<role>`` or ``<role>-<n>``."""
    name = str(instance).strip().lower()
    head, _, tail = name.rpartition("-")
    return head if head and tail.isdigit() else name


def _stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _paths_in(folder: Path) -> list:
    if not folder.is_dir():
        return []
    return sorted(folder.glob("M-*.json"))


def _paths(root: Path, instance: str) -> list:
    return _paths_in(instance_dir(root, instance))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(record, indent=2, sort_keys=True) + "\n")


def _next_id_in(folder: Path) -> str:
    high = 0
    for path in _paths_in(folder):
        try:
            high = max(high, int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"M-{high + 1:04d}"


def next_id(root: Path, instance: str) -> str:
    """The next ``M-nnnn`` for one mailbox; ids are per recipient, never reused."""
    return _next_id_in(instance_dir(root, instance))


def recipients(address: str, roster: list) -> list:
    """The local instances an address reaches; empty for a bus address."""
    scope, value = parse_address(address)
    if scope == "all":
        return sorted(pascal(name) for name in roster)
    if scope == "role":
        return sorted(pascal(name) for name in roster if role_of(name) == value.lower())
    if scope == "instance":
        return [pascal(value)]
    return []


def _expired(record: dict) -> bool:
    expires = record.get("expires_ts") or 0
    return bool(expires) and expires < time.time()


def _record(
    *,
    sender: str,
    recipient: str,
    scope: str,
    subject: str,
    priority: str,
    body: str,
    task: str,
    reply_to: str,
    message_id: str,
    session: str,
    ttl_hours: float,
) -> dict:
    created = time.time()
    return {
        "id": message_id,
        "from": sender,
        "to": recipient,
        "scope": scope,
        "priority": priority,
        "subject": subject,
        "body": body,
        "task": task,
        "reply_to": reply_to,
        "state": "pending",
        "created": _stamp(),
        "created_ts": created,
        "sender_session": session,
        "expires": ""
        if not ttl_hours
        else time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(created + float(ttl_hours) * 3600)),
        "expires_ts": 0 if not ttl_hours else created + float(ttl_hours) * 3600,
        "taken_by": "",
        "taken_at": "",
        "done_at": "",
        "result": "",
    }


def send_all(
    root: Path,
    *,
    sender: str,
    recipient: str,
    subject: str,
    priority: str = "normal",
    body: str = "",
    task: str = "",
    reply_to: str = "",
    roster: list | None = None,
    session: str = "",
    ttl_hours: float = 0,
) -> list:
    """Queue one message per address; a broadcast fans out here, at send time."""
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {', '.join(PRIORITIES)}")
    subject = " ".join(str(subject).split())[:SUBJECT_MAX]
    if not subject:
        raise ValueError("a message needs a subject")
    scope, value = parse_address(recipient)
    body = str(body)[:BODY_MAX]
    if scope in BUS_SCOPES:
        folder = bus_root(root) / bus_key(scope, value)
        with lock(bus_lock(root)):
            record = _record(
                sender=sender,
                recipient=f"{scope}:{value}",
                scope=scope,
                subject=subject,
                priority=priority,
                body=body,
                task=task,
                reply_to=reply_to,
                message_id=_next_id_in(folder),
                session=session,
                ttl_hours=ttl_hours,
            )
            _write(folder / f"{record['id']}.json", record)
        return [record]
    targets = recipients(recipient, sorted(roster or []))
    if not targets:
        raise ValueError(f"no instance answers '{recipient}' in this team")
    out = []
    for instance in targets:
        folder = instance_dir(root, instance)
        with lock(mailbox_lock(root)):
            record = _record(
                sender=sender,
                recipient=instance,
                scope=scope,
                subject=subject,
                priority=priority,
                body=body,
                task=task,
                reply_to=reply_to,
                message_id=_next_id_in(folder),
                session=session,
                ttl_hours=ttl_hours,
            )
            _write(folder / f"{record['id']}.json", record)
        out.append(record)
    return out


def send(
    root: Path,
    *,
    sender: str,
    recipient: str,
    subject: str,
    priority: str = "normal",
    body: str = "",
    task: str = "",
    reply_to: str = "",
    roster: list | None = None,
    session: str = "",
    ttl_hours: float = 0,
) -> dict:
    """Queue one message. Returns the first record; see ``send_all`` for a broadcast."""
    return send_all(
        root,
        sender=sender,
        recipient=recipient,
        subject=subject,
        priority=priority,
        body=body,
        task=task,
        reply_to=reply_to,
        roster=roster,
        session=session,
        ttl_hours=ttl_hours,
    )[0]


def _folder_rows(folder: Path, states: tuple) -> list:
    out = []
    for path in _paths_in(folder):
        record = _read(path)
        if record.get("state") not in states:
            continue
        if _expired(record):
            continue
        out.append(record)
    return out


def inbox(
    root: Path,
    instance: str,
    *,
    states: tuple = ("pending",),
    limit: int = 0,
    bus_keys: tuple = (),
) -> list:
    """Team rows then bus rows, in one (priority, created) order."""
    out = _folder_rows(instance_dir(root, instance), states)
    for key in bus_keys:
        out.extend(_folder_rows(bus_root(root) / key, states))
    out.sort(
        key=lambda r: (PRIORITY_RANK.get(r.get("priority", "normal"), 9), r.get("created_ts", 0))
    )
    return out[:limit] if limit else out


def counts(root: Path, instance: str, *, bus_keys: tuple = ()) -> dict:
    tally = {name: 0 for name in PRIORITIES}
    for record in inbox(root, instance, bus_keys=bus_keys):
        name = record.get("priority", "normal")
        tally[name] = tally.get(name, 0) + 1
    tally["pending"] = sum(tally[name] for name in PRIORITIES)
    return tally


def _locate(root: Path, instance: str, message_id: str, bus_keys: tuple) -> tuple:
    """(record path, lock path) for one id: the mailbox first, then the bus keys."""
    local = instance_dir(root, instance) / f"{message_id}.json"
    if local.is_file():
        return (local, mailbox_lock(root))
    for key in bus_keys:
        candidate = bus_root(root) / key / f"{message_id}.json"
        if candidate.is_file():
            return (candidate, bus_lock(root))
    return (None, None)


def find(root: Path, instance: str, message_id: str, bus_keys: tuple = ()) -> dict | None:
    path, _ = _locate(root, instance, message_id, bus_keys)
    return _read(path) if path else None


def take(root: Path, instance: str, message_id: str, by: str, bus_keys: tuple = ()) -> dict:
    path, lock_path = _locate(root, instance, message_id, bus_keys)
    if path is None:
        raise KeyError(f"no message {message_id} in {instance}'s mailbox")
    with lock(lock_path):
        record = _read(path)
        if record["state"] == "taken" and record.get("taken_by") not in ("", by):
            raise ValueError(
                f"{message_id} is already taken by {record['taken_by']}; one lane processes one message"
            )
        if record["state"] in ("done", "dropped"):
            raise ValueError(f"{message_id} is already {record['state']}")
        record["state"] = "taken"
        record["taken_by"] = by
        record["taken_at"] = _stamp()
        _write(path, record)
    return record


def finish(
    root: Path,
    instance: str,
    message_id: str,
    by: str,
    result: str,
    state: str = "done",
    bus_keys: tuple = (),
) -> dict:
    path, lock_path = _locate(root, instance, message_id, bus_keys)
    if path is None:
        raise KeyError(f"no message {message_id} in {instance}'s mailbox")
    with lock(lock_path):
        record = _read(path)
        if record["state"] in ("done", "dropped"):
            raise ValueError(f"{message_id} is already {record['state']}")
        if record.get("taken_by") and record["taken_by"] != by:
            raise ValueError(f"{message_id} was taken by {record['taken_by']}, not {by}")
        record["state"] = state
        record["taken_by"] = record.get("taken_by") or by
        record["done_at"] = _stamp()
        record["result"] = " ".join(str(result).split())[:400]
        _write(path, record)
    return record


def urgent_for(root: Path, instance: str, bus_keys: tuple = ()) -> list:
    """Pending urgent messages: the supervisor preempts for these."""
    return [m for m in inbox(root, instance, bus_keys=bus_keys) if m.get("priority") == "urgent"]


def packet_lines(root: Path, instance: str, bus_keys: tuple = ()) -> list:
    """The block a lane packet opens with: pending messages, priority order."""
    pending = inbox(root, instance, bus_keys=bus_keys)
    if not pending:
        return []
    tally = counts(root, instance, bus_keys=bus_keys)
    head = (
        f"## Messages for you ({tally['pending']} pending: "
        f"{tally['urgent']} urgent, {tally['high']} high, "
        f"{tally['normal']} normal, {tally['low']} low)"
    )
    lines = [head]
    for message in pending[:INBOX_LINES]:
        tag = message.get("priority", "normal")
        sender = message.get("from", "?")
        subject = message.get("subject", "")
        task = message.get("task") or ""
        suffix = f" (task {task})" if task else ""
        lines.append(f"- {message['id']} [{tag}] from {sender}: {subject}{suffix}")
    hidden = len(pending) - INBOX_LINES
    if hidden > 0:
        lines.append(f"- +{hidden} more in `tw message inbox --for {instance}`")
    if tally["urgent"]:
        lines.append(
            "Process every **urgent** message first: it is why your previous assignment "
            "was paused. `tw message take <id>`, do the work, `tw message done <id> --result ...`."
        )
    lines.append(
        "Higher priority first, then oldest. Re-check between steps with "
        f"`tw message inbox --for {instance}`; a message never interrupts you mid-step, "
        "so read the queue before you start something long."
    )
    return lines


def bus_keys_for(session: str = "", team: str = "") -> tuple:
    """The bus keys one lane answers to: its session, and its team when it has one."""
    keys = []
    if str(session).strip():
        keys.append(bus_key("session", str(session).strip()))
    if str(team).strip():
        keys.append(bus_key("team", str(team).strip()))
    return tuple(keys)


def add_parsers(sub, common) -> None:
    """`message` command surface: send, inbox, take, done."""
    s = sub.add_parser(
        "message",
        parents=[common],
        help="agent-to-agent mailbox: prioritised, queued, preemptible",
    )
    msub = s.add_subparsers(dest="message_cmd", required=True)
    p = msub.add_parser("send", parents=[common], help="queue a message for another agent")
    p.add_argument("--from", dest="sender", required=True, help="the sending instance")
    p.add_argument(
        "--to",
        required=True,
        help="one instance, *, role:<r>, team:<Name> or session:<id>",
    )
    p.add_argument("--subject", required=True, help="one line: what you need")
    p.add_argument(
        "--priority",
        default="normal",
        choices=PRIORITIES,
        help="urgent preempts the recipient's current assignment; normal queues",
    )
    p.add_argument("--body", default="", help="the detail the recipient needs")
    p.add_argument("--task", default="", help="the task this message concerns")
    p.add_argument("--reply-to", default="", help="the message id this answers")
    p.add_argument(
        "--ttl-hours",
        type=float,
        default=0,
        help="how long the message stays readable; 0 keeps it until it is closed",
    )
    p.add_argument(
        "--session",
        default="",
        help="the sending session id recorded on a bus message (default $PI_SESSION_ID)",
    )
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("inbox", parents=[common], help="pending messages, priority order")
    p.add_argument("--for", dest="recipient", required=True, help="the instance")
    p.add_argument("--all", action="store_true", help="include taken and done messages")
    p.add_argument("--json", action="store_true", help="one JSON object per message")
    p.add_argument(
        "--session",
        default="",
        help="also read the bus messages for this session (default $PI_SESSION_ID)",
    )
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("take", parents=[common], help="claim a message so one lane processes it")
    p.add_argument("message_id")
    p.add_argument("--for", dest="recipient", required=True)
    p.add_argument("--by", required=True, help="the instance taking it")
    p.add_argument("--session", default="", help="also look on the bus for this session")
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("done", parents=[common], help="close a message with its result")
    p.add_argument("message_id")
    p.add_argument("--for", dest="recipient", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--result", required=True, help="what you did, with the evidence")
    p.add_argument("--drop", action="store_true", help="close it as dropped instead of done")
    p.add_argument("--session", default="", help="also look on the bus for this session")
    p.set_defaults(func=cmd_message)


def cmd_message(args) -> int:
    from . import engine
    from .layout import list_agents
    from .names import pascal

    root = engine.project_root(args)
    verb = args.message_cmd
    session = (
        str(getattr(args, "session", "") or "").strip()
        or os.environ.get("PI_SESSION_ID", "").strip()
    )
    keys = bus_keys_for(session, str(getattr(args, "team", "") or ""))
    if verb == "send":
        known = {pascal(name) for name in list_agents(root)}
        sender = pascal(args.sender)
        try:
            scope, value = parse_address(args.to)
        except ValueError as exc:
            print(f"# {exc}")
            return 2
        if scope == "instance" and known and pascal(value) not in known:
            print(f"# no instance '{args.to}' in this team; known: {', '.join(sorted(known))}")
            return 2
        if scope == "role" and known and not recipients(args.to, sorted(known)):
            print(
                f"# no instance of role '{value}' in this team; known: {', '.join(sorted(known))}"
            )
            return 2
        try:
            records = send_all(
                root,
                sender=sender,
                recipient=args.to,
                subject=args.subject,
                priority=args.priority,
                body=args.body,
                task=args.task,
                reply_to=args.reply_to,
                roster=sorted(known),
                session=session,
                ttl_hours=args.ttl_hours,
            )
        except ValueError as exc:
            print(f"# {exc}")
            return 2
        first = records[0]
        for record in records:
            engine.ledger_append(
                root,
                "message.send",
                sender,
                record["id"],
                f"to {record['to']} [{record['priority']}] {record['subject']}"
                + (f" task={record['task']}" if record["task"] else ""),
                "",
                "",
            )
        where = "bus" if first["scope"] in BUS_SCOPES else "mailbox"
        extra = f" ({len(records)} recipients)" if len(records) > 1 else ""
        print(
            f"# {first['id']} queued for {first['to']} on the {where} "
            f"[{first['priority']}]: {first['subject']}{extra}"
        )
        if first["priority"] == "urgent":
            print(
                "# urgent: the next supervisor wave preempts that instance's lane, "
                f"pauses its task, and resumes it after `tw message done {first['id']}`"
            )
        return 0
    if verb == "inbox":
        states = ("pending", "taken", "done", "dropped") if args.all else ("pending",)
        rows = inbox(root, pascal(args.recipient), states=states, bus_keys=keys)
        tally = counts(root, pascal(args.recipient), bus_keys=keys)
        if args.json:
            for row in rows:
                print(json.dumps(row, sort_keys=True))
            return 0
        print(
            f"# Mailbox {pascal(args.recipient)}: {tally['pending']} pending "
            f"({tally['urgent']} urgent, {tally['high']} high, {tally['normal']} normal, "
            f"{tally['low']} low)"
        )
        if keys:
            print(f"# bus: {', '.join(keys)}")
        if not rows:
            print("- empty")
            return 0
        for row in rows:
            task = f" task={row['task']}" if row.get("task") else ""
            print(
                f"- {row['id']} [{row['priority']}] {row['state']} from {row['from']}: "
                f"{row['subject']}{task} ({row['created']})"
            )
        return 0
    if verb == "take":
        try:
            record = take(root, pascal(args.recipient), args.message_id, pascal(args.by), keys)
        except (KeyError, ValueError) as exc:
            print(f"# {exc}")
            return 2
        engine.ledger_append(
            root, "message.take", record["taken_by"], record["id"], record["subject"], "", ""
        )
        print(f"# {record['id']} taken by {record['taken_by']} [{record['priority']}]")
        if record.get("body"):
            print(record["body"])
        return 0
    if verb == "done":
        state = "dropped" if args.drop else "done"
        try:
            record = finish(
                root,
                pascal(args.recipient),
                args.message_id,
                pascal(args.by),
                args.result,
                state,
                keys,
            )
        except (KeyError, ValueError) as exc:
            print(f"# {exc}")
            return 2
        engine.ledger_append(
            root, "message.done", record["taken_by"], record["id"], record["result"], "", ""
        )
        print(f"# {record['id']} {record['state']}: {record['result']}")
        return 0
    return 2
