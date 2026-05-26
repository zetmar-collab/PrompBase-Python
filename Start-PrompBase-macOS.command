#!/bin/bash
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  python3 promptbase.py
elif command -v python >/dev/null 2>&1; then
  python promptbase.py
else
  echo "Python 3 nie zostal znaleziony."
  echo "Zainstaluj Python 3: https://www.python.org/downloads/"
  read -r -p "Enter aby zamknac..."
fi
