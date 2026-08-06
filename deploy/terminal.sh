#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source deploy/cluster.sh

PYTHONPATH=src .venv/bin/python -m channels.terminal.main
