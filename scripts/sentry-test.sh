#!/bin/bash
# A simple script to demonstrate Sentry error reporting.

set -e

# This function will be called on script error
handle_error() {
  echo "An error occurred. Reporting to Sentry..."
  # In a real scenario, you would use sentry-cli here.
  # For now, we'll just simulate it.
  echo "Event sent to Sentry:"
  echo "  - Message: Script failed"
  echo "  - Script: $0"
  echo "  - Line: $1"
  echo "  - Exit Code: $2"
}

trap 'handle_error $LINENO $?' ERR

echo "Running a command that will succeed..."
ls -l

echo "Running a command that will fail..."
command_that_does_not_exist
