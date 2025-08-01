#!/bin/bash

# Auto push script for nahmey-api repository
# This script automatically stages, commits, and pushes changes to the repository

echo "🚀 Starting auto push process..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Check if there are any changes to commit
if git diff --quiet && git diff --staged --quiet; then
    echo "✅ No changes to commit"
    exit 0
fi

# Add all changes
echo "📝 Staging all changes..."
git add .

# Get current timestamp for commit message
timestamp=$(date "+%Y-%m-%d %H:%M:%S")

# Create commit message
commit_message="Auto commit: $timestamp"

# Allow custom commit message as parameter
if [ ! -z "$1" ]; then
    commit_message="$1"
fi

# Commit changes
echo "💾 Committing changes with message: '$commit_message'"
git commit -m "$commit_message"

# Check if commit was successful
if [ $? -eq 0 ]; then
    echo "✅ Commit successful"
else
    echo "❌ Commit failed"
    exit 1
fi

# Push to remote repository
echo "🌐 Pushing to remote repository..."
git push

# Check if push was successful
if [ $? -eq 0 ]; then
    echo "✅ Push successful! Changes have been uploaded to the repository."
else
    echo "❌ Push failed. Please check your network connection and repository permissions."
    exit 1
fi

echo "🎉 Auto push completed successfully!"