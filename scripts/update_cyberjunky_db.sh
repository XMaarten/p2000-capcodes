#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-/data/p2000.sqlite3}"
SOURCE="${2:-data/capcodes.sqlite3}"

p2000-capcodes update-addon-db "$TARGET" --source "$SOURCE"
