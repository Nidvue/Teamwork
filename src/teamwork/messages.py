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

State is one JSON file per message under ``Runtime/Mailbox/<Instance>/``, mutated
under a lock. Nothing here is a second ledger: the ledger records that a message
was sent, taken and done; the mailbox holds the message itself.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import DIR_RUNTIME
from .io import atomic_write, lock

DIR_MAILBOX = "Mailbox"
PRIORITIES = ("urgent", "high", "normal", "low")
PRIORITY_RANK = {name: index for index, name in enumerate(PRIORITIES)}
STATES = ("pending", "taken", "done", "dropped")
SUBJECT_MAX = 120
BODY_MAX = 4000
INBOX_LINES = 8


def mailbox_dir(root: Path) -> Path:
    return root / DIR_RUNTIME / DIR_MAILBOX


def instance_dir(root: Path, instance: str) -> Path:
    return mailbox_dir(root) / instance


def mailbox_lock(root: Path) -> Path:
    return root / DIR_RUNTIME / "Locks" / "mailbox.lock"


def _stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _paths(root: Path, instance: str) -> list:
    folder = instance_dir(root, instance)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("M-*.json"))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(record, indent=2, sort_keys=True) + "\n")


def next_id(root: Path, instance: str) -> str:
    """The next ``M-nnnn`` for one mailbox; ids are per recipient, never reused."""
    high = 0
    for path in _paths(root, instance):
        try:
            high = max(high, int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"M-{high + 1:04d}"


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
) -> dict:
    """Queue one message. Returns the record; refuses an unknown priority."""
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {', '.join(PRIORITIES)}")
    subject = " ".join(str(subject).split())[:SUBJECT_MAX]
    if not subject:
        raise ValueError("a message needs a subject")
    folder = instance_dir(root, recipient)
    with lock(mailbox_lock(root)):
        folder.mkdir(parents=True, exist_ok=True)
        record = {
            "id": next_id(root, recipient),
            "from": sender,
            "to": recipient,
            "priority": priority,
            "subject": subject,
            "body": str(body)[:BODY_MAX],
            "task": task,
            "reply_to": reply_to,
            "state": "pending",
            "created": _stamp(),
            "created_ts": time.time(),
            "taken_by": "",
            "taken_at": "",
            "done_at": "",
            "result": "",
        }
        _write(folder / f"{record['id']}.json", record)
    return record


def inbox(root: Path, instance: str, *, states: tuple = ("pending",), limit: int = 0) -> list:
    """The recipient's messages in priority order, then oldest first."""
    out = []
    for path in _paths(root, instance):
        record = _read(path)
        if record.get("state") in states:
            out.append(record)
    out.sort(
        key=lambda r: (PRIORITY_RANK.get(r.get("priority", "normal"), 9), r.get("created_ts", 0))
    )
    return out[:limit] if limit else out


def counts(root: Path, instance: str) -> dict:
    tally = {name: 0 for name in PRIORITIES}
    for record in inbox(root, instance):
        tally[record.get("priority", "normal")] = tally.get(record.get("priority", "normal"), 0) + 1
    tally["pending"] = sum(tally[name] for name in PRIORITIES)
    return tally


def find(root: Path, instance: str, message_id: str) -> dict | None:
    path = instance_dir(root, instance) / f"{message_id}.json"
    return _read(path) if path.is_file() else None


def take(root: Path, instance: str, message_id: str, by: str) -> dict:
    with lock(mailbox_lock(root)):
        record = find(root, instance, message_id)
        if record is None:
            raise KeyError(f"no message {message_id} in {instance}'s mailbox")
        if record["state"] == "taken" and record.get("taken_by") not in ("", by):
            raise ValueError(
                f"{message_id} is already taken by {record['taken_by']}; one lane processes one message"
            )
        if record["state"] in ("done", "dropped"):
            raise ValueError(f"{message_id} is already {record['state']}")
        record["state"] = "taken"
        record["taken_by"] = by
        record["taken_at"] = _stamp()
        _write(instance_dir(root, instance) / f"{message_id}.json", record)
    return record


def finish(
    root: Path, instance: str, message_id: str, by: str, result: str, state: str = "done"
) -> dict:
    with lock(mailbox_lock(root)):
        record = find(root, instance, message_id)
        if record is None:
            raise KeyError(f"no message {message_id} in {instance}'s mailbox")
        if record["state"] in ("done", "dropped"):
            raise ValueError(f"{message_id} is already {record['state']}")
        if record.get("taken_by") and record["taken_by"] != by:
            raise ValueError(f"{message_id} was taken by {record['taken_by']}, not {by}")
        record["state"] = state
        record["taken_by"] = record.get("taken_by") or by
        record["done_at"] = _stamp()
        record["result"] = " ".join(str(result).split())[:400]
        _write(instance_dir(root, instance) / f"{message_id}.json", record)
    return record


def urgent_for(root: Path, instance: str) -> list:
    """Pending urgent messages: the supervisor preempts for these."""
    return [m for m in inbox(root, instance) if m.get("priority") == "urgent"]


def packet_lines(root: Path, instance: str) -> list:
    """The block a lane packet opens with: pending messages, priority order."""
    pending = inbox(root, instance)
    if not pending:
        return []
    tally = counts(root, instance)
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
    p.add_argument("--to", required=True, help="the recipient instance")
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
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("inbox", parents=[common], help="pending messages, priority order")
    p.add_argument("--for", dest="recipient", required=True, help="the instance")
    p.add_argument("--all", action="store_true", help="include taken and done messages")
    p.add_argument("--json", action="store_true", help="one JSON object per message")
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("take", parents=[common], help="claim a message so one lane processes it")
    p.add_argument("message_id")
    p.add_argument("--for", dest="recipient", required=True)
    p.add_argument("--by", required=True, help="the instance taking it")
    p.set_defaults(func=cmd_message)
    p = msub.add_parser("done", parents=[common], help="close a message with its result")
    p.add_argument("message_id")
    p.add_argument("--for", dest="recipient", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--result", required=True, help="what you did, with the evidence")
    p.add_argument("--drop", action="store_true", help="close it as dropped instead of done")
    p.set_defaults(func=cmd_message)


def cmd_message(args) -> int:
    from . import engine
    from .layout import list_agents
    from .names import pascal

    root = engine.project_root(args)
    verb = args.message_cmd
    if verb == "send":
        known = {pascal(name) for name in list_agents(root)}
        sender, recipient = pascal(args.sender), pascal(args.to)
        if known and recipient not in known:
            print(f"# no instance '{args.to}' in this team; known: {', '.join(sorted(known))}")
            return 2
        try:
            record = send(
                root,
                sender=sender,
                recipient=recipient,
                subject=args.subject,
                priority=args.priority,
                body=args.body,
                task=args.task,
                reply_to=args.reply_to,
            )
        except ValueError as exc:
            print(f"# {exc}")
            return 2
        engine.ledger_append(
            root,
            "message.send",
            sender,
            record["id"],
            f"to {recipient} [{record['priority']}] {record['subject']}"
            + (f" task={record['task']}" if record["task"] else ""),
            "",
            "",
        )
        print(
            f"# {record['id']} queued for {recipient} [{record['priority']}]: {record['subject']}"
        )
        if record["priority"] == "urgent":
            print(
                "# urgent: the next supervisor wave preempts that instance's lane, "
                f"pauses its task, and resumes it after `tw message done {record['id']}`"
            )
        return 0
    if verb == "inbox":
        states = ("pending", "taken", "done", "dropped") if args.all else ("pending",)
        rows = inbox(root, pascal(args.recipient), states=states)
        tally = counts(root, pascal(args.recipient))
        if args.json:
            for row in rows:
                print(json.dumps(row, sort_keys=True))
            return 0
        print(
            f"# Mailbox {pascal(args.recipient)}: {tally['pending']} pending "
            f"({tally['urgent']} urgent, {tally['high']} high, {tally['normal']} normal, "
            f"{tally['low']} low)"
        )
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
            record = take(root, pascal(args.recipient), args.message_id, pascal(args.by))
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
                root, pascal(args.recipient), args.message_id, pascal(args.by), args.result, state
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
