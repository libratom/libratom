#!/usr/bin/env bash

set -x

pip-compile -o requirements.txt requirements.in --upgrade --quiet "$@"
pip-compile -o requirements-dev.txt requirements-dev.in requirements.in --upgrade --quiet "$@"
