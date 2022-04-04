#!/usr/bin/env sh
set -o errexit
set -o nounset
set -e

: "${cmd:=run_all_tests}"

pyclean () {
  # Cleaning cache:
  find . | grep -E '(__pycache__|\.py[cod]$)' | xargs rm -rf
}

run_code_quality () {
  echo "Run mypy check"
  mypy toolset examples/*

  echo "Running code-quality check"
  xenon --max-absolute B --max-modules A --max-average A toolset  --exclude toolset/testing/matching.py

  echo "Checking if all the dependencies are secure and do not have any known vulnerabilities:"
  safety check --bare --full-report -i 38624 -i 38625
  # ignore safety uvicorn warning
  # uvicorn fixed CVEs in 0.11.7 but safety-db use old data

  echo "Running code security check"
  bandit -r toolset
}

run_pytest () {
  echo "Run pytest"
  # use different cov report to catch coverage percent in gitlab
  PYTHONPATH=. pytest --cov-report=term
}

run_fmt_check () {
  echo "Run formatting (isort and black) check"
  isort --check-only --diff --recursive toolset tests
  black . --check

}

run_flake8 () {
  echo "Run flake8 check"
  flakehell lint toolset tests
}

run_all_tests () {
  run_code_quality
  run_fmt_check
  run_flake8
  run_pytest
}

if [ $# -eq 0 ]; then
  echo "run all checks and tests"
  run_all_tests
else
  echo "called $*"
  "$@"
fi
