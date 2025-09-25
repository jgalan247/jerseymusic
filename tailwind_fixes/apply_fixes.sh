#!/bin/bash
# Script to apply Tailwind fixes to your Django project

echo "Creating components directory..."
mkdir -p templates/components

echo "Copying component templates..."
cp components/*.html templates/components/

echo "Component templates installed!"
echo "Now update your templates according to the fix commands."
echo "Use 'cat claude_prompt.md' to see the full instructions for Claude."
