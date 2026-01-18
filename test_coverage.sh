#!/bin/bash
# Run pytest with coverage report

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default conda environment if not set
CONDA_ENV=${CONDA_ENV:-larsnet-midi}

echo "Running tests with coverage (conda env: $CONDA_ENV)..."
conda run -n "$CONDA_ENV" pytest --cov=. --cov-report=term-missing --cov-report=html -q
