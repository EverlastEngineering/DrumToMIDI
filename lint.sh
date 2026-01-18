#!/bin/bash
# Run ruff linter

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default conda environment if not set
CONDA_ENV=${CONDA_ENV:-drumtomidi}

echo "Running ruff linter (conda env: $CONDA_ENV)..."
conda run -n "$CONDA_ENV" ruff check . --statistics
