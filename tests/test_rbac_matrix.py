"""One test per row of data/security_matrix.csv.

actor    = an identity fixture name (anonymous, normal_user, admin_user, ...)
target   = self (actor's id) or other (another_user's id)
payload  = key=value;key=value; {id} and {admin_username} fill in at run time
Add a row to add a test — this file doesn't change."""
import csv
from pathlib import Path

import pytest

MATRIX = Path(__file__).resolve().parent.parent / "data" / "security_matrix.csv"


def load_matrix():
    with MATRIX.open(newline="") as f:
        rows = list(csv.DictReader(f))
    params = []
    for row in rows:
        marks = [getattr(pytest.mark, row["area"]), getattr(pytest.mark, row["classification"])]
        if row["classification"] == "security_hypothesis":
            marks.append(pytest.mark.xfail(reason=f"FINDING: {row['rule']}"))
        params.append(pytest.param(row, id=row["id"], marks=marks))
    return params


def _payload(text):
    """'a=1;b=x' -> {"a": 1, "b": "x"} (digits become ints)."""
    if not text:
        return None
    pairs = (kv.split("=", 1) for kv in text.split(";"))
    return {k: (int(v) if v.isdigit() else v) for k, v in pairs}


@pytest.mark.parametrize("row", load_matrix())
def test_security_matrix(row, request, another_user):
    actor = request.getfixturevalue(row["actor"])      # the fixture named in the CSV
    target_id = actor.user_id if row["target"] == "self" else another_user.user_id

    subs = {"id": target_id}
    if "{admin_username}" in row["path"] + row["payload"]:
        subs["admin_username"] = request.getfixturevalue("admin_user").username
    path = row["path"].format(**subs)
    payload = _payload(row["payload"].format(**subs)) if row["payload"] else None

    body, status = actor.api_client.request(row["method"], path, json=payload)
    request.node.actual_status = status        # recorded for the report

    assert status == int(row["expected"]), (
        f"{row['id']} — {row['rule']}: {row['actor']} {row['method']} {path} "
        f"expected {row['expected']}, got {status}"
    )
