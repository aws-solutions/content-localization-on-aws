#!/bin/bash
###############################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   Copy templates and assets generated by the build script into S3 bucket
#
# USAGE:
#  ./sync-s3-dist.sh [-h] [-v] --template-bucket {TEMPLATE_BUCKET} --code-bucket {CODE_BUCKET} --version {VERSION} --region {REGION} --profile {PROFILE}
#    TEMPLATE_BUCKET should be the name for the S3 bucket location where Media Insights on AWS
#      cloud formation templates should be saved.
#    CODE_BUCKET should be the name for the S3 bucket location where cloud
#      formation templates should find Lambda source code packages.
#    VERSION can be anything but should be in a format like v1.0.0 just to be consistent
#      with the official solution release labels.
#    REGION needs to be in a format like us-east-1
#    PROFILE is optional. It's the profile that you have setup in ~/.aws/credentials
#      that you want to use for AWS CLI commands.
#
#    The following options are available:
#
#     -h | --help       Print usage
#     -v | --verbose    Print script debug info
#
###############################################################################

usage() {
  msg "$msg"
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--profile PROFILE] --template-bucket TEMPLATE_BUCKET --code-bucket CODE_BUCKET --version VERSION --region REGION

Available options:

-h, --help        Print this help and exit (optional)
-v, --verbose     Print script debug info (optional)
--template-bucket S3 bucket to put cloud formation templates
--code-bucket     S3 bucket to put Lambda code packages
--version         Arbitrary string indicating build version
--region          AWS Region, formatted like us-west-2
--profile         AWS profile for CLI commands (optional)
EOF
  exit 1
}

msg() {
  echo >&2 -e "${1-}"
}

parse_params() {
  # default values of variables set from params
  flag=0
  param=''

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -v | --verbose) set -x ;;
    --template-bucket)
      global_bucket="${2}"
      shift
      ;;
    --code-bucket)
      regional_bucket="${2}"
      shift
      ;;
    --version)
      version="${2}"
      shift
      ;;
    --region)
      region="${2}"
      shift
      ;;
    --profile)
      profile="${2}"
      shift
      ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  args=("$@")

  # check required params and arguments
  [[ -z "${global_bucket}" ]] && usage "Missing required parameter: template-bucket"
  [[ -z "${regional_bucket}" ]] && usage "Missing required parameter: code-bucket"
  [[ -z "${version}" ]] && usage "Missing required parameter: version"
  [[ -z "${region}" ]] && usage "Missing required parameter: region"

  return 0
}

parse_params "$@"
msg "Build parameters:"
msg "- Template bucket: ${global_bucket}"
msg "- Code bucket: ${regional_bucket}-${region}"
msg "- Version: ${version}"
msg "- Region: ${region}"
msg "- Profile: ${profile}"

# Make sure aws cli is installed
if [[ ! -x "$(command -v aws)" ]]; then
echo "ERROR: This script requires the AWS CLI to be installed. Please install it then run again."
exit 1
fi

# Get reference for all important folders
build_dir="$PWD"
source_dir="$build_dir/../source"
consumer_dir="$build_dir/../source/consumer"
global_dist_dir="$build_dir/global-s3-assets"
regional_dist_dir="$build_dir/regional-s3-assets"

echo "------------------------------------------------------------------------------"
echo "Copy dist to S3"
echo "------------------------------------------------------------------------------"
echo "Validating ownership of distribution buckets before copying deployment assets to them..."
# Get account id
account_id=$(aws sts get-caller-identity --query Account --output text $(if [ ! -z $profile ]; then echo "--profile $profile"; fi))
if [ $? -ne 0 ]; then
  die "ERROR: Failed to get AWS account ID"
fi
# Validate ownership of $global_dist_dir
aws s3api head-bucket --bucket $global_bucket --expected-bucket-owner $account_id $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
if [ $? -ne 0 ]; then
  die "ERROR: Your AWS account does not own s3://$global_bucket/"
fi
# Validate ownership of ${regional_bucket}-${region}
aws s3api head-bucket --bucket ${regional_bucket}-${region} --expected-bucket-owner $account_id $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
if [ $? -ne 0 ]; then
  die "ERROR: Your AWS account does not own s3://${regional_bucket}-${region} "
fi
# Copy deployment assets to distribution buckets
cd "$build_dir"/ || exit 1
echo "Copying the prepared distribution to:"
echo "s3://$global_bucket/content-localization-on-aws/$version/"
echo "s3://${regional_bucket}-${region}/content-localization-on-aws/$version/"

s3domain="s3.$region.amazonaws.com"
set -x
aws s3 sync $global_dist_dir s3://$global_bucket/content-localization-on-aws/$version/ $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
aws s3 sync $regional_dist_dir s3://${regional_bucket}-${region}/content-localization-on-aws/$version/ $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
set +x

echo "------------------------------------------------------------------------------"
echo "S3 packaging complete"
echo "------------------------------------------------------------------------------"

echo ""
echo "Template to deploy:"
echo ""
echo "With existing Media Insights on AWS deployment:"
echo "TEMPLATE='"https://"$global_bucket"."$s3domain"/content-localization-on-aws/"$version"/content-localization-on-aws-use-existing-mie-stack.template"'"
echo "Without existing Media Insights on AWS deployment:"
echo "TEMPLATE='"https://"$global_bucket"."$s3domain"/content-localization-on-aws/"$version"/content-localization-on-aws.template"'"

echo "https://"$global_bucket"."$s3domain"/content-localization-on-aws/"$version"/content-localization-on-aws.template" > template_url_that_deploys_mie_as_nested_stack.txt
echo "https://"$global_bucket"."$s3domain"/content-localization-on-aws/"$version"/content-localization-on-aws-use-existing-mie-stack.template" > template_url_that_uses_an_existing_mie_stack.txt

echo "Done"
exit 0
