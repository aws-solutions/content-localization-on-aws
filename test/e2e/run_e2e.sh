#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# PURPOSE: This script runs our pytest e2e test suite.
#
# PRELIMINARY:
#  You must have a functioning Content Localization on AWS deployment and
#  set the required environment variables.
#  See the testing README.md for more details.
#
# USAGE:
#  ./run_e2e.sh
#
###############################################################################
# User-defined environment variables

if [ -z "${MIE_REGION:-}" ]
then
    echo "You must set the env variable 'MIE_REGION' to the AWS region your Media Insights on AWS stack is install in. Quitting."
    exit 1
fi

if [ -z "${MIE_STACK_NAME:-}" ]
then
    echo "You must set the env variable 'MIE_STACK_NAME' to the name of your Media Insights on AWS stack. Quitting."
    exit 1
fi

if [ -z "${AWS_ACCESS_KEY_ID:+mask}" ]
then
    echo "You must set the env variable 'AWS_ACCESS_KEY_ID' to a valid IAM access key id. Quitting."
    exit 1
fi

if [ -z "${AWS_SECRET_ACCESS_KEY:+mask}" ]
then
    echo "You must set the env variable 'AWS_SECRET_ACCESS_KEY' to a valid IAM secret access key. Quitting."
    exit 1
fi

if [ -z "${APP_PASSWORD:+mask}" ]
then
    echo "You must set the env variable 'APP_PASSWORD' to a valid password to use to log in to the web application. Quitting."
    exit 1
fi

#################### Nothing for users to change below here ####################

# Make sure working directory is the directory containing this script
cd "$(dirname "${BASH_SOURCE[0]}")"

# Make sure we clean up
cleanup_before_exit() {
    cleanup $?
}

cleanup() {
    # Reset the signals to default behavior
    trap - SIGINT SIGTERM EXIT
    echo "------------------------------------------------------------------------------"
    echo "Cleaning up"
    echo "------------------------------------------------------------------------------"

    # Deactivate and remove the temporary python virtualenv used to run this script
    [ -n "${VIRTUAL_ENV:-}" ] && deactivate
    [ -n "$VENV" ] && [ -d "$VENV" ] && rm -rf "$VENV"
    rm -rf  __pycache__
    exit ${1:-0}
}

# Create and activate a temporary Python environment for this script.
echo "------------------------------------------------------------------------------"
echo "Creating a temporary Python virtualenv for this script"
echo "------------------------------------------------------------------------------"
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
if ! command -v python3 &>/dev/null; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi

# Make temporary directory for the virtual environment
VENV=$(mktemp -d)

# Trap exits so we are sure to clean up the virtual environment
trap cleanup_before_exit SIGINT SIGTERM EXIT

# Create and activate the virtual environment
python3 -m venv "$VENV" || exit $?
source $VENV/bin/activate || exit $?

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install required Python libraries."
    exit 1
fi

function query_info_about_stacks() {
    local stack_type=unknown
    local -r stack_name=${MIE_STACK_NAME}
    # We're going to find the dataplane bucket name in the Media insights on AWS stack.
    # Let's check the stack named by $MIE_STACK_NAME and make adjustments as necessary.
    # First we will fetch details about the stack  (i.e., ID, Parameters, and Outputs).
    for i in $(aws --region $MIE_REGION cloudformation describe-stacks --stack-name ${MIE_STACK_NAME} --no-paginate --output text \
        --query 'Stacks[0].{Stack:[{Key:StackStatus,Value:StackId}], Parameters:Parameters, Outputs:Outputs[*][@.{OutputKey:OutputKey, OutputValue:OutputValue}], Parent:{Key:`ParentId`, Value:ParentId}}' \
        | grep -e '^OUTPUTS[[:space:]]\+\(ContentLocalizationSolution\|DataplaneBucket\)\>' -e '^PARAMETERS[[:space:]]\+\(AdminEmail\|MieStackName\)\>' -e '^STACK\>' -e '^PARENT\>' \
        | cut -f2- \
        | tr '\t' '=' \
        | sort)
    do
        case ${i%%=*} in
            AdminEmail)
                [ -n "${APP_USERNAME:-}" ] || export APP_USERNAME="${i#*=}"
                ;;
            ContentLocalizationSolution)
                [ -n "${APP_ENDPOINT:-}" ] || export APP_ENDPOINT="${i#*=}"
                stack_type=cl_with_nested_mi
                ;;
            DataplaneBucket)
                export DATAPLANE_BUCKET="${i#*=}"
                stack_type=mi
                ;;
            MieStackName)
                export MIE_STACK_NAME="${i#*=}"
                stack_type=cl_use_existing_mi
                ;;
            CREATE_COMPLETE)
                local -r stackid="${i#*=}"
                ;;
            ParentId)
                local -r parentid="${i#*=}"
                ;;
            *)
                >&2 echo "Stack deployment may not be complete: ${stack_name}"
                return 1
                ;;
        esac
    done

    # The stack should be one of three types of stacks
    #   1. Media insights on AWS
    #   2. Content localization on AWS with nested Media insights on AWS stack
    #   3. Content localization on AWS using existing Media insights on AWS stack
    case ${stack_type} in
        mi)
            # If the Media insights on AWS stack is nested in a Content localization on AWS stack
            # and we don't have the endpoint and username variables defined, we can fetch those.
            if [ -z "${APP_ENDPOINT}" -o -z "${APP_USERNAME}" ] && [ "${parentid%%:*}" = arn ]
            then
                for i in $(aws --region $MIE_REGION cloudformation describe-stacks --no-paginate --output text \
                    --query "Stacks[?StackId==\`${parentid}\`].{Parameters:Parameters, Outputs:Outputs[*][@.{OutputKey:OutputKey, OutputValue:OutputValue}]}" \
                    | grep -e '^OUTPUTS[[:space:]]\+ContentLocalizationSolution\>' -e '^PARAMETERS[[:space:]]\+AdminEmail\>' \
                    | cut -f2- \
                    | tr '\t' '=' \
                    | sort)
                do
                    case ${i%%=*} in
                        AdminEmail)
                            [ -n "${APP_USERNAME:-}" ] || export APP_USERNAME="${i#*=}"
                            ;;
                        ContentLocalizationSolution)
                            [ -n "${APP_ENDPOINT:-}" ] || export APP_ENDPOINT="${i#*=}"
                            ;;
                    esac
                done
            fi
            ;;
        cl_with_nested_mi)
            # We know the Media insights on AWS stack is a nested stack so we need to find it.
            for i in $(aws --region $MIE_REGION cloudformation describe-stacks --no-paginate --output text \
                --query "Stacks[?ParentId==\`${stackid}\`].{StackName:StackName, Outputs:Outputs[?OutputKey=='DataplaneBucket']}[?length(Outputs)>\`0\`].{Stack:{Key:\`StackName\`, Value:StackName}, Outputs:Outputs[*][@.{OutputKey:OutputKey, OutputValue:OutputValue}]}" \
                | cut -f2- \
                | tr '\t' '=' \
                | sort)
            do
                case ${i%%=*} in
                    DataplaneBucket)
                        export DATAPLANE_BUCKET="${i#*=}"
                        ;;
                    StackName)
                        export MIE_STACK_NAME="${i#*=}"
                        ;;
                    ContentLocalizationSolution)
                        [ -n "${APP_ENDPOINT:-}" ] || export APP_ENDPOINT="${i#*=}"
                        ;;
                esac
            done
            ;;
        cl_use_existing_mi)
            # We now know the name of the real Media insights on AWS stack;
            # query the stack for the dataplane bucket name.
            export DATAPLANE_BUCKET=$(aws --region $MIE_REGION cloudformation list-exports --query "Exports[?Name==\`${MIE_STACK_NAME}:DataplaneBucket\`].Value" --no-paginate --output text)
            ;;
        unknown)
            # We don't know what stack we're looking at.
            >&2 echo "The stack doesn't appear to be Media insights on AWS nor Content localization on AWS: ${stack_name}"
            return 1
            ;;
    esac
}

echo "------------------------------------------------------------------------------"
echo "Setup test environment variables"

export TEST_MEDIA_PATH="../test-media/"
export TEST_IMAGE="sample-image.jpg"
export TEST_VIDEO="sample-video.mp4"
export TEST_AUDIO="sample-audio.m4a"
export TEST_VOCABULARY_FILE="uitestvocabulary"
query_info_about_stacks || exit $?

echo "------------------------------------------------------------------------------"


# Final checks for environment variables. We may resolve these automatically
# in query_info_about_stacks. But, if they can't be resolved, the user must
# supply values for the tests to run.

if [ -z "${APP_USERNAME:-}" ]
then
    echo "You must set the env variable 'APP_USERNAME' with a valid username to use to log in to the web application. Quitting."
    exit
fi

if [ -z "${APP_ENDPOINT:-}" ]
then
    echo "You must set the env variable 'APP_ENDPOINT' with the url for the Content Localization web application. Quitting."
    exit
fi

pytest -s -W ignore::DeprecationWarning -p no:cacheproviders "$@"

######TESTING: test a single file
#pytest -s -W ignore::DeprecationWarning -p no:cacheproviders test_workflow_reprocess.py
#pytest -s -W ignore::DeprecationWarning -p no:cacheproviders test_app.py
######TESTING: test a single file

if [ $? -eq 0 ]; then
    rm *.png
    exit 0
else
    # Copy browser screenshots from github workspace to S3 in case they're needed
    # for troubleshooting e2e errors.
    ls -1 *.png | while read line; do aws s3 cp $line s3://$DATAPLANE_BUCKET/; done
    exit 1
fi

cleanup $?
