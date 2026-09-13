# Space42 API security tests — common commands. Run `make help` to list them.
SHELL := bash
# Uses the first Python found in this order (3.12 recommended; 3.10–3.13 supported).
PYTHON ?= $(shell command -v python3.12 || command -v python3.13 || command -v python3.11 || command -v python3.10 || command -v python3)
VENV   := .venv
PYTEST := $(VENV)/bin/pytest

.PHONY: help install test auth users matrix exposure findings contract report evidence package clean

help:            ## show this help
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install:         ## create the venv and install pinned dependencies
	@test -n "$(PYTHON)" || { echo "No python3 found. Install Python 3.12 from https://www.python.org/downloads/"; exit 1; }
	@$(PYTHON) -c 'import sys; v = sys.version_info; print(f"using Python {v.major}.{v.minor} ({sys.executable})"); sys.exit(0 if (3, 10) <= (v.major, v.minor) <= (3, 13) else 1)' \
		|| { echo "Python 3.10-3.13 is required (3.12 recommended). Found: $(PYTHON)"; exit 1; }
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo "done. next: make test"

test:            ## run the whole suite (reports/report.html + junit.xml + findings.md)
	$(PYTEST)

auth:            ## authentication tests only
	$(PYTEST) tests/test_auth.py

users:           ## users service contract tests only
	$(PYTEST) tests/test_users.py

matrix:          ## the RBAC / ownership security matrix only
	$(PYTEST) tests/test_rbac_matrix.py

exposure:        ## data-exposure tests only
	$(PYTEST) tests/test_data_exposure.py

findings:        ## only the security-hypothesis tests (the documented findings)
	$(PYTEST) -m security_hypothesis

contract:        ## only the contract tests (documented behaviour, expected to pass)
	$(PYTEST) -m contract

report:          ## open the last HTML report (macOS / Linux; otherwise open the file yourself)
	@open reports/report.html 2>/dev/null || xdg-open reports/report.html 2>/dev/null || echo "Open reports/report.html in your browser"

evidence:        ## run the suite and snapshot the results into evidence/ (ships with the submission)
	mkdir -p evidence
	set -o pipefail; $(PYTEST) | sed "s|$(CURDIR)|.|g" | tee evidence/console.txt   # strip the local absolute path
	cp reports/report.html reports/junit.xml reports/findings.md evidence/
	@echo "snapshot written to evidence/ (report.html, junit.xml, findings.md, console.txt)"

package:         ## zip the project for submission (no venv, caches, logs or .env) -> ../space42-submission.zip
	rm -f ../space42-submission.zip
	zip -qr ../space42-submission.zip . -x '.venv/*' '.git/*' '.idea/*' '*/__pycache__/*' '__pycache__/*' \
		'.pytest_cache/*' 'logs/*' 'reports/*' '.env' '.DS_Store' '*/.DS_Store' '*.pdf'
	@echo "created ../space42-submission.zip"

clean:           ## remove caches, logs and generated reports
	rm -rf .pytest_cache reports/* logs/* $$(find . -name __pycache__ -not -path './$(VENV)/*')
