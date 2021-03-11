# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# White box testing for the base Media Insights Engine stack and Rekognition
# workflow.
#
# PRECONDITIONS:
# MIE base stack must be deployed in your AWS account
#
# Boto3 will raise a deprecation warning (known issue). It's safe to ignore.
#
# USAGE:
#   cd tests/
#   pytest -s -W ignore::DeprecationWarning -p no:cacheprovider
#
###############################################################################


import urllib3
import time


def test_workflow_execution(workflow_api, dataplane_api, stack_resources, testing_env_variables):
    workflow_api = workflow_api()
    dataplane_api = dataplane_api()

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    test_execution = {
        "Name": "VODSubtitlesVideoWorkflow",
        "Configuration": {
            "TranslateStage2": {
                "TranslateWebCaptions": {
                    "MediaType": "MetadataOnly",
                    "Enabled": True,
                    "TargetLanguageCodes": [
                      "es"
                    ],
                    "SourceLanguageCode": "en",
                    "TerminologyNames": [],
                    "ParallelDataNames": []
                }
            },
            "defaultVideoStage2": {
                "faceSearch": {
                   "MediaType": "Video",
                   "Enabled": False
                },
                "GenericDataLookup": {
                    "MediaType": "Video",
                    "Enabled": False
                    }
            }
        },
        "Input": {
            "Media": {
                "Video": {
                    "S3Bucket": stack_resources['DataplaneBucket'],
                    "S3Key": 'upload/' + testing_env_variables['SAMPLE_VIDEO']
                }
            }
        }
    }
    
    # Check that the application workflow exists
    workflow_request = workflow_api.get_workflow_request("VODSubtitlesVideoWorkflow")
    assert workflow_request.status_code == 200

    # create workflow execution

    workflow_execution_request = workflow_api.create_workflow_execution_request(test_execution)
    assert workflow_execution_request.status_code == 200

    workflow_execution_response = workflow_execution_request.json()
    workflow_execution_id = workflow_execution_response["Id"]
    asset_id = workflow_execution_response["AssetId"]

    time.sleep(5)

    # wait for workflow to complete

    workflow_processing = True

    while workflow_processing:
        get_workflow_execution_request = workflow_api.get_workflow_execution_request(workflow_execution_id)
        get_workflow_execution_response = get_workflow_execution_request.json()

        assert get_workflow_execution_request.status_code == 200


        workflow_status = get_workflow_execution_response["Status"]
        print(f'Workflow Status: {workflow_status}')

        allowed_statuses = ["Started", "Queued", "Complete"]

        assert workflow_status in allowed_statuses

        if workflow_status == "Complete":
            workflow_processing = False
        else:
            print('Sleeping for 30 seconds before retrying')
            time.sleep(30)

    # Get asset mediainfo from dataplane

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(asset_id, "Mediainfo")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(asset_id, "WebCaptions_en")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(asset_id, "WebCaptions_es")
    assert asset_mediainfo_request.status_code == 200

    print(asset_mediainfo_request.json())
