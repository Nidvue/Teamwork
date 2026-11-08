"""The task parser's field allow-list is bound to the record it parses (T-0020).

Finding 14 of the M19 audit: `parse_tasks` re-listed 44 field names by hand while
`new_task` declared the record's keys. They agreed when the audit ran, but nothing
held them together, so a field added to `new_task` would parse as empty and the
gate state it carries would be lost silently. This test is the binding: the
allow-list must equal the record's own keys, minus the three `parse_tasks` assigns
itself.
"""

from __future__ import annotations

from teamwork import records

PARSER_ASSIGNED = {"id", "title", "body"}


def test_the_allow_list_is_exactly_the_record_keys_the_parser_does_not_assign() -> None:
    declared = set(records.new_task("probe"))
    assert set(records.TASK_META_FIELDS) == declared - PARSER_ASSIGNED


def test_a_new_record_field_without_an_allow_list_entry_fails_this_test() -> None:
    """The failure the binding prevents: a key in new_task that the parser drops."""
    declared = set(records.new_task("probe"))
    missing = declared - PARSER_ASSIGNED - set(records.TASK_META_FIELDS)
    assert missing == set(), (
        "these keys are on the task record but not in TASK_META_FIELDS, so parse_tasks "
        f"would silently drop them: {sorted(missing)}"
    )
