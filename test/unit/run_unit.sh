#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# PURPOSE: This script runs our pytest unit test suite.
#
# PRELIMINARY:
#  Set the required environment variables; see the testing README.md for more
#  details.
#
# USAGE:
#  ./run_unit.sh [COMPONENT...]
#
#   where COMPONENT is an optional sub-set of components to run tests for.
#   The sub-directories contained within this directory match the components
#   so, COMPONENT is one or more sub-directories. If COMPONENT is not specified,
#   all unit tests will run for all components.
#
###############################################################################

#################### Nothing for users to change below here ####################

# Make sure working directory is the directory containing this script
cd "$(dirname "${BASH_SOURCE[0]}")"

# Returns shell SUCCESS value if ${1} is a SUCCESS value; otherwise FAIL.
is_set() {
    return ${1:-1}
}

log_step() {
    echo "------------------------------------------------------------------------------"
    echo "$*"
    echo "------------------------------------------------------------------------------"
}

log_step "Setup test environment variables"

TEMP_VENV=''
VENV=''
[ -n "${CACHED_TEST_VENV:-}" ]; declare -ri cache_venv=$?
is_set $cache_venv && [ -f "${CACHED_TEST_VENV:-}/bin/activate" ]; declare -ri cache_hit=$?

source_dir=`cd ../../source; pwd`
coverage_reports_dir="$(cd ..; pwd)/coverage-reports"

# Make sure we clean up
cleanup_before_exit() {
    cleanup $?
}

# Clean up temporary files
cleanup() {
    # Reset the signals to default behavior
    trap - SIGINT SIGTERM EXIT
    log_step "Cleaning up"

    # Deactivate and remove the temporary python virtualenv used to run this script
    [ -n "${VIRTUAL_ENV:-}" ] && deactivate
    [ -n "${TEMP_VENV:-}" ] && [ -d "$TEMP_VENV" ] && rm -rf "$TEMP_VENV"
    rm -rf  __pycache__ .coverage
    exit ${1:-0}
}

# Install packages defined in ${1:-.}/requirements.txt if it exists
pip_install_requirements() {
    # Skip install if we are using the cached venv
    is_set $cache_hit && return 0

    local -r src_dir="${1:-.}"
    if [ "$src_dir" = . ]
    then
        local -r req_file=requirements.txt
    else
        local -r req_file="${src_dir}/requirements.txt"
    fi

    if [ -f "${req_file}" -a -r "${req_file}" ]
    then
        [ "$src_dir" = . ] || pushd "${src_dir}" &>/dev/null || exit 1
        pip install -r requirements.txt || {
            echo "ERROR: Failed to install required Python libraries at ${req_file}"
            exit 1
        }
        [ "$src_dir" = . ] || popd &>/dev/null || exit 1
    fi
}

# Install packages defined in source/${1}/requirements.txt if it exists
pip_install_source_requirements() {
    log_step "Installing required Python packages for ${tc}"
    pip_install_requirements "${source_dir}/${1}"
}

# Create and activate a temporary Python environment for this script.

log_step "Creating a temporary Python virtualenv for this script"
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
if ! command -v python3 &>/dev/null; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi

# Make temporary directory for the virtual environment
if is_set $cache_venv
then
    VENV="$CACHED_TEST_VENV"
else
    VENV="$(mktemp -d)"
    TEMP_VENV="${VENV}"
fi

# Trap exits so we are sure to clean up the virtual environment
trap cleanup_before_exit SIGINT SIGTERM EXIT

# Create and activate the virtual environment
[ -f "$VENV/bin/activate" ] || python3 -m venv "$VENV" || exit $?
source "$VENV/bin/activate" || exit $?

# Install packages into the virtual environment
pip_install_requirements


# Run all test cases specified
run_tests() {
    while [ $# -ne 0 ]; do
        local tc="${1%/}"
        shift

        # Make sure required packages are installed
        pip_install_source_requirements ${tc}

        log_step "Running ${tc} unit tests"
        coverage_report_path="$coverage_reports_dir/coverage-source-${tc}.xml"
        pytest "${tc}" -s -W ignore::DeprecationWarning \
            -W 'ignore:IAMAuthorizer is not a supported in local mode:UserWarning' -p no:cacheprovider \
            --cov="$source_dir/${tc}" --cov-report=term --cov-report=xml:$coverage_report_path \
            || exit 1

        sed -i.orig -e "s,<source>$source_dir,<source>source,g" $coverage_report_path
        rm -f $coverage_reports_dir/*.orig
    done
}

if [ $# -gt 0 ]; then
    # Run all tests spcified as command line arguments
    run_tests "$@"
else
    # No tests specified so run all of them found in sub-directories
    log_step "Running all unit tests"
    run_tests */
fi

cleanup $?
