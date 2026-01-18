#!/bin/bash
# Run tests quickly without coverage

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default conda environment if not set
CONDA_ENV=${CONDA_ENV:-drumtomidi}

echo "Running tests (conda env: $CONDA_ENV)..."
conda run -n "$CONDA_ENV" pytest -x
