#!/bin/bash
###############################################################################
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   Build cloud formation templates for the Media Insights Engine
#
# USAGE:
#  ./build.sh {SOURCE-BUCKET} {VERSION} {REGION} [PROFILE]
#    SOURCE-BUCKET should be the name for the S3 bucket location where the
#      template will source the Lambda code from.
#    VERSION should be in a format like v1.0.0
#    REGION needs to be in a format like us-east-1
#    PROFILE is optional. It's the profile  that you have setup in ~/.aws/config
#      that you want to use for aws CLI commands.
#
###############################################################################


# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name,  version where the lambda code will eventually reside and the region of the deploy."
    echo "USAGE: ./build.sh SOURCE-BUCKET VERSION REGION [PROFILE]"
    echo "For example: ./build.sh mie01 2.0.0 us-east-1 default"
    exit 1
fi

bucket=$1
version=$2
region=$3
if [ -n "$4" ]; then profile=$4; fi

# Check if region is supported:
if [ "$region" != "us-east-1" ] &&
   [ "$region" != "us-east-2" ] &&
   [ "$region" != "us-west-1" ] &&
   [ "$region" != "us-west-2" ] &&
   [ "$region" != "eu-west-1" ] &&
   [ "$region" != "eu-west-2" ] &&
   [ "$region" != "eu-central-1" ] &&
   [ "$region" != "ap-south-1" ] &&
   [ "$region" != "ap-northeast-1" ] &&
   [ "$region" != "ap-southeast-1" ] &&
   [ "$region" != "ap-southeast-2" ] &&
   [ "$region" != "ap-northeast-1" ] &&
   [ "$region" != "ap-northeast-2" ]; then
   echo "ERROR. Rekognition operatorions are not supported in region $region"
   exit 1
fi


# Setup deployment variables
template_dir="../cloudformation"
consumer_dir="../consumer"
helper_dir="../helper"
website_dir="../src"

dist_dir="$PWD/dist"
website_dist_dir="../dist"

# Create and activate a temporary Python environment for this script.
echo "------------------------------------------------------------------------------"
echo "Creating a temporary Python virtualenv for this script"
echo "------------------------------------------------------------------------------"
python -c "import os; print (os.getenv('VIRTUAL_ENV'))" | grep -q None
if [ $? -ne 0 ]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
command -v python3
if [ $? -ne 0 ]; then
    echo "ERROR: install Python3 before running this script"
    exit 1
fi
VENV=$(mktemp -d)
python3 -m venv "$VENV"
source "$VENV"/bin/activate


# Delete and create new dist directory
echo "rm -rf $dist_dir"
rm -rf "$dist_dir"

echo "mkdir -p $dist_dir"
mkdir -p "$dist_dir"

echo "------------------------------------------------------------------------------"
echo "CloudFormation Templates"
echo "------------------------------------------------------------------------------"

echo "Preparing template files:"

cp "$template_dir/aws-vod-subtitles-deploy-mie.yaml" "$dist_dir/aws-vod-subtitles-deploy-mie.template"
cp "$template_dir/aws-vod-subtitles.yaml" "$dist_dir/aws-vod-subtitles.template"
cp "$template_dir/aws-content-analysis-elasticsearch.yaml" "$dist_dir/aws-content-analysis-elasticsearch.template"
cp "$template_dir/aws-content-analysis-auth.yaml" "$dist_dir/aws-content-analysis-auth.template"
cp "$template_dir/aws-content-analysis-web.yaml" "$dist_dir/aws-content-analysis-web.template"
cp "$template_dir/aws-vod-subtitles-video-workflow.yaml" "$dist_dir/aws-vod-subtitles-video-workflow.template"
cp "$template_dir/aws-content-analysis-image-workflow.yaml" "$dist_dir/aws-content-analysis-image-workflow.template"
cp "$template_dir/string.yaml" "$dist_dir/string.template"


find "$dist_dir"

echo "Updating code source bucket in template files with '$bucket'"
echo "Updating solution version in template files with '$version'"

new_bucket="s/%%BUCKET_NAME%%/$bucket/g"
new_version="s/%%VERSION%%/$version/g"

# Update templates in place. Copy originals to [filename].orig
sed -i.orig -e "$new_bucket" "$dist_dir/aws-vod-subtitles-deploy-mie.template"
sed -i.orig -e "$new_version" "$dist_dir/aws-vod-subtitles-deploy-mie.template"

sed -i.orig -e "$new_bucket" "$dist_dir/aws-vod-subtitles.template"
sed -i.orig -e "$new_version" "$dist_dir/aws-vod-subtitles.template"

sed -i.orig -e "$new_bucket" "$dist_dir/aws-content-analysis-elasticsearch.template"
sed -i.orig -e "$new_version" "$dist_dir/aws-content-analysis-elasticsearch.template"

sed -i.orig -e "$new_bucket" "$dist_dir/aws-content-analysis-auth.template"
sed -i.orig -e "$new_version" "$dist_dir/aws-content-analysis-auth.template"

sed -i.orig -e "$new_bucket" "$dist_dir/aws-content-analysis-web.template"
sed -i.orig -e "$new_version" "$dist_dir/aws-content-analysis-web.template"


echo "------------------------------------------------------------------------------"
echo "Elasticsearch consumer Function"
echo "------------------------------------------------------------------------------"

echo "Building Elasticsearch Consumer function"
cd "$consumer_dir" || exit 1
pwd
[ -e dist ] && rm -r dist
mkdir -p dist
[ -e package ] && rm -r package
mkdir -p package
echo "preparing packages from requirements.txt"
# Package dependencies listed in requirements.txt
pushd package || exit 1
# Handle distutils install errors with setup.cfg
touch ./setup.cfg
echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg
if ! [ -x "$(command -v pip3)" ]; then
  echo "pip3 not installed. This script requires pip3. Exiting."
  exit 1
else
    pip3 install --quiet -r ../requirements.txt --target .
fi
zip -q -r9 ../dist/esconsumer.zip .
popd || exit 1


zip -q -g dist/esconsumer.zip ./*.py
cp "./dist/esconsumer.zip" "$dist_dir/esconsumer.zip"

echo "------------------------------------------------------------------------------"
echo "Website Helper"
echo "------------------------------------------------------------------------------"

echo "Building website helper function"
cd "$helper_dir" || exit 1
[ -e dist ] && rm -r dist
mkdir -p dist
zip -q -g ./dist/websitehelper.zip ./website_helper.py
cp "./dist/websitehelper.zip" "$dist_dir/websitehelper.zip"


echo "------------------------------------------------------------------------------"
echo "Website"
echo "------------------------------------------------------------------------------"


echo "Building Vue.js website"
cd "$website_dir/" || exit 1
echo "Installing node dependencies"
npm install
echo "Compiling the vue app"
npm run build
echo "Built demo webapp"


echo "------------------------------------------------------------------------------"
echo "Copy dist to S3"
echo "------------------------------------------------------------------------------"

echo "Copying the prepared distribution to S3..."
for file in "$dist_dir"/*.zip
do
  if [ -n "$profile" ]; then
    aws s3 cp "$file" s3://"$bucket"/vod-subtitles-solution/"$version"/code/ --profile "$profile"
  else
    aws s3 cp "$file" s3://"$bucket"/vod-subtitles-solution/"$version"/code/
  fi
done
for file in "$dist_dir"/*.template
do
  if [ -n "$profile" ]; then
    aws s3 cp "$file" s3://"$bucket"/vod-subtitles-solution/"$version"/cf/ --profile "$profile"
  else
    aws s3 cp "$file" s3://"$bucket"/vod-subtitles-solution/"$version"/cf/
  fi
done
echo "Uploading the vod subtitles web app..."
if [ -n "$profile" ]; then
  aws s3 cp "$website_dist_dir" s3://"$bucket"/vod-subtitles-solution/"$version"/code/website --recursive --profile "$profile"
else
  aws s3 cp "$website_dist_dir" s3://"$bucket"/vod-subtitles-solution/"$version"/code/website --recursive
fi

echo "------------------------------------------------------------------------------"
echo "S3 packaging complete"
echo "------------------------------------------------------------------------------"

# Deactivate and remove the temporary python virtualenv used to run this script
deactivate
rm -rf "$VENV"

echo "------------------------------------------------------------------------------"
echo "Cleaning up complete"
echo "------------------------------------------------------------------------------"

echo ""
echo "Templates to deploy:"
echo ""
echo "With existing MIE deployment:"
echo "TEMPLATE='"https://"$bucket".s3."$region".amazonaws.com/vod-subtitles-solution/"$version"/cf/aws-vod-subtitles.template"'"
echo "Without existing MIE deployment:"
echo "TEMPLATE='"https://"$bucket".s3."$region".amazonaws.com/vod-subtitles-solution/"$version"/cf/aws-vod-subtitles-deploy-mie.template"'"

touch templateUrlMieDevelopment.txt
echo "https://"$bucket".s3."$region".amazonaws.com/vod-subtitles-solution/"$version"/cf/aws-vod-subtitles.template" > templateUrlMieDevelopment.txt
touch templateUrlMieRelease.txt
echo "https://"$bucket".s3."$region".amazonaws.com/vod-subtitles-solution/"$version"/cf/aws-vod-subtitles-deploy-mie.template" > templateUrlMieRelease.txt

echo "------------------------------------------------------------------------------"
echo "Done"
echo "------------------------------------------------------------------------------"
exit 0
