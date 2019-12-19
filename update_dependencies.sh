#!/usr/bin/env bash

set -x

pip-compile -o requirements.txt requirements.in --upgrade --quiet "$@"
pip-compile -o requirements-dev.txt requirements-dev.in requirements.in --upgrade --quiet "$@"

# Python 3.6 dependency only
# Add to .in files if supported by pip-compile
echo -e "\n\n# PY36\nimportlib_resources; python_version < '3.7'" >> requirements.txt
echo -e "\n\n# PY36\nimportlib_resources; python_version < '3.7'" >> requirements-dev.txt
