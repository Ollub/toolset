#!/bin/bash

ARGS=${1:-.}
echo "Run isort"
isort --recursive toolset tests
echo "Run add-trailing-comma"
find toolset -name '*.py' -exec add-trailing-comma {} +
find tests -name '*.py' -exec add-trailing-comma {} +
echo "Run black"
black toolset tests examples
