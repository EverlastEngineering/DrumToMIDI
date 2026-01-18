#!/bin/bash
# Start the web UI server

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default conda environment if not set
CONDA_ENV=${CONDA_ENV:-larsnet-midi}

echo "Starting web UI (conda env: $CONDA_ENV)..."
echo "Access at: http://localhost:5001"
conda run -n "$CONDA_ENV" python -m webui.app
