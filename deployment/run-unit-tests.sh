#!/bin/bash

# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh

# Run unit tests
echo "Running unit tests"

echo "------------------------------------------------------------------------------"
echo "Installing Dependencies And Testing Modules"
echo "------------------------------------------------------------------------------"

../test/unit/run_unit.sh
