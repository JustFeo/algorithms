#!/bin/bash

# Usage: ./git_auto_push.sh [commit message]

# Default commit message if none provided
COMMIT_MSG=${1:-"Auto-commit: update files"}

echo "Staging all changes..."
git add .

echo "Committing with message: '$COMMIT_MSG'"
git commit -m "$COMMIT_MSG"

echo "Pushing to remote repository..."
git push

echo "Done!" 