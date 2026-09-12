"""Readable reporting (loaded by conftest.py via pytest_plugins).

Every test gets a one-line description, an area, and the API calls it made. From that:
  - HTML report: a Description column, plus three tables above the results —
    the security matrix (expected vs actual), all other test cases (with the APIs
    they called), and the findings.
  - Console: a grouped "security summary" at the end of the run.
  - reports/findings.md: the findings as a markdown table, for the README.
"""
import html
import json
from pathlib import Path
from urllib.parse import urlencode

import pytest
from pytest_metadata.plugin import metadata_key

from config import get_settings
from utils import api_client

AREAS = ("auth", "users", "rbac", "ownership", "exposure")
FINDINGS_MD = Path(__file__).resolve().parent.parent / "reports" / "findings.md"   # project root
LABEL = {"passed": "PASS", "finding": "FINDING", "failed": "FAIL",
         "unexpected pass": "UNEXPECTED PASS", "skipped": "SKIPPED"}
KIND = {"contract": "Documented behaviour", "security_hypothesis": "Security expectation"}

_RESULTS = {}   # nodeid -> call-phase report, in execution order


# --- collect one record per test ------------------------------------------------

def pytest_configure(config):
    config.stash[metadata_key]["Target"] = get_settings().base_url


def _describe(item) -> str:
    """Matrix rule, FINDING reason, or a readable form of the test name."""
    row = item.callspec.params.get("row") if hasattr(item, "callspec") else None
    if row:
        prefix = "FINDING: " if row["classification"] == "security_hypothesis" else ""
        return f"{prefix}{row['rule']}"
    xfail = item.get_closest_marker("xfail")
    if xfail:
        return xfail.kwargs.get("reason", "")
    name = item.name.removeprefix("test_").replace("_", " ")
    return f"{item.cls.__name__.removeprefix('Test')}: {name}" if item.cls else name


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """Remember which API calls were made inside this test's body (not its fixtures)."""
    start = len(api_client.CALLS)
    yield
    item.calls = api_client.CALLS[start:]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    report.description = _describe(item)
    report.area = next((m.name for m in item.iter_markers() if m.name in AREAS), "")
    report.matrix_row = item.callspec.params.get("row") if hasattr(item, "callspec") else None
    report.actual = getattr(item, "actual_status", None)
    report.calls = getattr(item, "calls", [])
    # Severity and OWASP category: from the matrix row, else from @pytest.mark markers
    # on hand-written tests, else "-".
    row = report.matrix_row
    sev_m, owa_m = item.get_closest_marker("severity"), item.get_closest_marker("owasp")
    report.severity = (row.get("severity") if row else None) or (sev_m.args[0] if sev_m and sev_m.args else None)
    report.owasp = (row.get("owasp") if row else None) or (owa_m.args[0] if owa_m and owa_m.args else None)
    if report.when == "call":
        _RESULTS[item.nodeid] = report


def _outcome(report) -> str:
    """passed | finding (expected xfail) | unexpected pass | failed | skipped"""
    if hasattr(report, "wasxfail"):
        return "finding" if report.skipped else "unexpected pass"
    return report.outcome


def _sev(r) -> str:
    return getattr(r, "severity", None) or "-"


def _owasp(r) -> str:
    return getattr(r, "owasp", None) or "-"


def _drift(r) -> str:
    """Flag when this run's status differs from the status recorded in the CSV's
    `observed` column — i.e. the gap changed shape (or the API was fixed / down)."""
    m = getattr(r, "matrix_row", None)
    obs = m.get("observed") if m else None
    if obs and obs != "-" and r.actual is not None and str(r.actual) != str(obs):
        return f"  ⚠ CHANGED (observed {obs}, now {r.actual})"
    return ""


# --- HTML report ------------------------------------------------------------------

def pytest_html_report_title(report):
    report.title = "Space42 — DummyJSON API Security Test Report"


def pytest_html_results_table_header(cells):
    cells.insert(2, "<th>Description</th>")


def pytest_html_results_table_row(report, cells):
    cells.insert(2, f"<td>{getattr(report, 'description', '')}</td>")


_STYLE = """<style>
.s42{border-collapse:collapse;margin:6px 0 18px;font-size:13px}
.s42 th,.s42 td{border:1px solid #ccc;padding:3px 8px;text-align:left;vertical-align:top;white-space:pre-line}
.s42 th{background:#f3f3f3}
.s42 .passed{background:#e6f4ea}.s42 .finding{background:#fff4e5}
.s42 .failed,.s42 .unexpected{background:#fde8e8}.s42 .skipped{background:#f0f0f0}
</style>"""


def _table(title, headers, rows):
    """rows = [(css_class, [cell, ...]), ...]"""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        f"<tr class='{cls.split()[0]}'>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in cells) + "</tr>"
        for cls, cells in rows
    )
    return f"<h2>{title}</h2><table class='s42'><tr>{head}</tr>{body}</table>"


def _api_lines(calls) -> str:
    """One line per call: METHOD /path?query"""
    return "\n".join(f"{c['method']} {c['path']}" + (f"?{urlencode(c['params'])}" if c["params"] else "")
                     for c in calls) or "—"


def _body_lines(calls) -> str:
    """One line per call: the (redacted) JSON body, or — for calls without one."""
    return "\n".join(json.dumps(c["json"]) if c["json"] else "—" for c in calls) or "—"


def pytest_html_results_summary(prefix, summary, postfix):
    reports = list(_RESULTS.values())
    findings = [r for r in reports if _outcome(r) == "finding"]
    passed = [r for r in reports if _outcome(r) == "passed"]
    postfix.append(_STYLE + f"<p><b>Contract checks passed: {len(passed)}</b> &nbsp;&nbsp; "
                            f"<b>Findings (secure behaviour not met): {len(findings)}</b></p>")

    matrix = [r for r in reports if r.matrix_row]
    if matrix:
        rows = []
        for r in matrix:
            m = r.matrix_row
            req = f"{m['method']} {m['path']}" + (f"   body: {m['payload']}" if m["payload"] else "")
            rows.append((_outcome(r), [
                m["id"], _sev(r), _owasp(r), m["rule"], m["actor"], req, m["target"],
                m["expected"], r.actual if r.actual is not None else "—",
                LABEL[_outcome(r)] + _drift(r), KIND.get(m["classification"], m["classification"]),
            ]))
        postfix.append(_table(
            "Security matrix — test cases and results (data/security_matrix.csv)",
            ["ID", "Sev", "OWASP", "Test case", "Actor", "Request", "Target",
             "Expected", "Actual", "Result", "Type"],
            rows,
        ))

    others = [r for r in reports if not r.matrix_row and r.area]
    if others:
        postfix.append(_table(
            "Test cases — authentication, users, data exposure",
            ["Area", "Test case", "API", "Request body", "Result", "Type"],
            [(_outcome(r), [r.area, r.description.removeprefix("FINDING: "),
                            _api_lines(r.calls), _body_lines(r.calls),
                            LABEL[_outcome(r)],
                            "Security expectation" if hasattr(r, "wasxfail") else "Documented behaviour"])
             for r in others],
        ))

    if findings:
        postfix.append(_table(
            "Findings", ["#", "Sev", "OWASP", "Area", "Test", "Finding (secure behaviour not met)"],
            [("finding", [i, _sev(r), _owasp(r), r.area, r.nodeid.split("::", 1)[1],
                          r.description.removeprefix("FINDING: ") + _drift(r)])
             for i, r in enumerate(findings, 1)],
        ))


# --- console summary + findings.md ------------------------------------------------

def pytest_terminal_summary(terminalreporter):
    reports = list(_RESULTS.values())
    findings = [r for r in reports if _outcome(r) == "finding"]
    passed = [r for r in reports if _outcome(r) == "passed"]
    failed = terminalreporter.stats.get("failed", [])
    errors = terminalreporter.stats.get("error", [])

    terminalreporter.section("security summary")
    extra = f"    FAILED: {len(failed)}    ERRORS: {len(errors)}" if (failed or errors) else ""
    terminalreporter.write_line(
        f"contract checks passed: {len(passed)}    findings: {len(findings)}{extra}")
    for r in findings:
        terminalreporter.write_line(
            f"  [{_sev(r):6}][{r.area:9}] {r.description.removeprefix('FINDING: ')}{_drift(r)}")
    if failed or errors:
        terminalreporter.write_line(
            "  note: FAILED/ERRORS above are real problems (a broken test, an unexpected pass, "
            "or the API being unreachable) — not documented findings.")

    FINDINGS_MD.parent.mkdir(exist_ok=True)
    lines = ["| # | Sev | OWASP | Area | Test | Finding (secure behaviour not met) |",
             "|---|---|---|---|---|---|"]
    for i, r in enumerate(findings, 1):
        test = r.nodeid.split("::", 1)[1]
        desc = r.description.removeprefix("FINDING: ") + _drift(r)
        lines.append(f"| {i} | {_sev(r)} | {_owasp(r)} | {r.area} | `{test}` | {desc} |")
    FINDINGS_MD.write_text("\n".join(lines) + "\n")
