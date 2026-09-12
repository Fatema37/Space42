"""Data-driven security matrix: one test per row of data/security_matrix.csv.

Columns: id, area, actor, method, path, target, payload, expected, classification,
         severity, owasp, observed, rule
  actor           the name of any identity fixture in auth_fixtures.py (anonymous, normal_user, admin_user, ...)
  target          self -> the actor's own id      other -> another_user's id
  path/payload    {id} -> the target id; {admin_username} -> the admin's username (resolved at run time)
  payload         key=value pairs separated by ';' (request body), empty for GET/DELETE
  classification  contract -> expected PASS;  security_hypothesis -> strict xfail = documented finding
  severity/owasp  shown in the report and findings table (finding rows only)
  observed        the status seen when the matrix was written; the report flags it if it changes
Add a row to add a test; this file does not change."""
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
    """'a=1;b=x' -> {"a": 1, "b": "x"} (digits become ints, like a JSON body would carry)."""
    if not text:
        return None
    pairs = (kv.split("=", 1) for kv in text.split(";"))
    return {k: (int(v) if v.isdigit() else v) for k, v in pairs}


@pytest.mark.parametrize("row", load_matrix())
def test_security_matrix(row, request, another_user):
    actor = request.getfixturevalue(row["actor"])      # any identity fixture, looked up by name
    target_id = actor.user_id if row["target"] == "self" else another_user.user_id

    subs = {"id": target_id}
    if "{admin_username}" in row["path"] + row["payload"]:
        subs["admin_username"] = request.getfixturevalue("admin_user").username
    path = row["path"].format(**subs)
    payload = _payload(row["payload"].format(**subs)) if row["payload"] else None

    body, status = actor.api_client.request(row["method"], path, json=payload)
    request.node.actual_status = status        # shown as "Actual" in the HTML matrix table

    assert status == int(row["expected"]), (
        f"{row['id']} — {row['rule']}: {row['actor']} {row['method']} {path} "
        f"expected {row['expected']}, got {status}"
    )
