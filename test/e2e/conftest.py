######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import pytest
import boto3
import json
import requests
import time
import logging
import re
import os
import urllib3
from requests_aws4auth import AWS4Auth

REQUEST_TIMEOUT = None

# Fixture for retrieving env variables


@pytest.fixture(scope='session')
def testing_env_variables():
    print('Setting variables for tests')
    try:
        if "USE_EXISTING_WORKFLOW" in os.environ:
            use_existing_workflow = os.environ['USE_EXISTING_WORKFLOW']
        else:
            use_existing_workflow = False

        test_env_vars = {
            'MEDIA_PATH': os.environ['TEST_MEDIA_PATH'],
            'SAMPLE_VIDEO': os.environ['TEST_VIDEO'],
            'SAMPLE_AUDIO': os.environ['TEST_AUDIO'],
            'SAMPLE_VOCABULARY_FILE': os.environ['TEST_VOCABULARY_FILE'],
            'REGION': os.environ['MIE_REGION'],
            'MIE_STACK_NAME': os.environ['MIE_STACK_NAME'],
            'ACCESS_KEY': os.environ['AWS_ACCESS_KEY_ID'],
            'SECRET_KEY': os.environ['AWS_SECRET_ACCESS_KEY'],
            'APP_USERNAME': os.environ['APP_USERNAME'],
            'APP_PASSWORD': os.environ['APP_PASSWORD'],
            'APP_ENDPOINT': os.environ['APP_ENDPOINT'],
            'USE_EXISTING_WORKFLOW': use_existing_workflow
        }

        # Optional session token may be set if we are using temporary STS credentials.
        session_token = os.environ.get('AWS_SESSION_TOKEN', '')
        if len(session_token):
            test_env_vars['SESSION_TOKEN'] = session_token

    except KeyError as e:
        logging.error(
            "ERROR: Missing a required environment variable for testing: {variable}".format(variable=e))
        raise Exception(e)
    else:
        return test_env_vars


# Fixture for stack resources


@pytest.fixture(scope='session')
def stack_resources(testing_env_variables):
    print('Validating Stack Resources')
    resources = {}
    # is the workflow api and operator library present?

    client = boto3.client(
        'cloudformation', region_name=testing_env_variables['REGION'])
    response = client.describe_stacks(
        StackName=testing_env_variables['MIE_STACK_NAME'])
    outputs = response['Stacks'][0]['Outputs']

    for output in outputs:
        if (output["OutputKey"] != 'TestStack'):
            resources[output["OutputKey"]] = output["OutputValue"]

    assert "WorkflowApiEndpoint" in resources
    assert "DataplaneApiEndpoint" in resources

    api_endpoint_regex = ".*.execute-api." + \
        testing_env_variables['REGION']+".amazonaws.com/api/.*"

    assert re.match(api_endpoint_regex, resources["WorkflowApiEndpoint"])

    response = client.describe_stacks(
        StackName=resources["OperatorLibraryStack"])
    outputs = response['Stacks'][0]['Outputs']

    for output in outputs:
        # These tests don't depend on TestStack.  They should pass whether it is deployed or not
        
            resources[output["OutputKey"]] = output["OutputValue"]
    
    expected_resources = ['WorkflowApiRestID', 'DataplaneBucket', 'DataPlaneHandlerArn', 'WorkflowCustomResourceArn', 'AnalyticsStreamArn', 'DataplaneApiEndpoint', 'WorkflowApiEndpoint', 'DataplaneApiRestID', 'OperatorLibraryStack', 'PollyOperation', 'ContentModerationOperationImage', 'GenericDataLookupOperation', 'comprehendEntitiesOperation', 'FaceSearch', 'FaceSearchOperationImage', 'MediainfoOperationImage', 'TextDetection', 'TextDetectionOperationImage', 'CreateSRTCaptionsOperation', 'ContentModeration', 'WebCaptionsOperation', 'WebToVTTCaptionsOperation', 'PollyWebCaptionsOperation', 'WaitOperation', 'TranslateWebCaptionsOperation', 'CelebRecognition', 'LabelDetection', 'FaceDetection', 'PersonTracking', 'MediaconvertOperation', 'FaceDetectionOperationImage', 'MediainfoOperation', 'ThumbnailOperation', 'TechnicalCueDetection', 'CreateVTTCaptionsOperation', 'CelebrityRecognitionOperationImage', 'TranslateOperation', 'comprehendPhrasesOperation', 'WebToSRTCaptionsOperation', 'shotDetection', 'LabelDetectionOperationImage', "Version", "TranscribeAudioOperation", "TranscribeVideoOperation", "MieKMSArn", "MieKMSAlias", "MieSQSQueue", "MediaInsightsEnginePython39LayerArn", "MieSNSTopic", "MieKMSId"]
    
    assert set(resources.keys()) == set(expected_resources)

    return resources


# This fixture uploads the sample media objects for testing.


@pytest.fixture(scope='session', autouse=True)
def upload_media(testing_env_variables, stack_resources):
    print('Uploading Test Media')
    s3 = boto3.client('s3', region_name=testing_env_variables['REGION'])
    # Upload test media files
    s3.upload_file(testing_env_variables['MEDIA_PATH'] + testing_env_variables['SAMPLE_VIDEO'],
                   stack_resources['DataplaneBucket'], 'upload/' + testing_env_variables['SAMPLE_VIDEO'])
    s3.upload_file(testing_env_variables['MEDIA_PATH'] + testing_env_variables['SAMPLE_VOCABULARY_FILE'],
                   stack_resources['DataplaneBucket'],  testing_env_variables['SAMPLE_VOCABULARY_FILE'])
    # Wait for fixture to go out of scope:
    yield upload_media


# Workflow API Class


@pytest.mark.usefixtures("upload_media")
class WorkflowAPI:
    def __init__(self, stack_resources, testing_env_variables):
        self.env_vars = testing_env_variables
        self.stack_resources = stack_resources
        self.auth = AWS4Auth(testing_env_variables['ACCESS_KEY'], testing_env_variables['SECRET_KEY'],
                             testing_env_variables['REGION'], 'execute-api',
                             session_token=testing_env_variables.get('SESSION_TOKEN'))

    # Workflow Methods

    def get_workflow_request(self, workflow):
        get_workflow_response = requests.get(
            self.stack_resources["WorkflowApiEndpoint"] + '/workflow/' + workflow, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)
        return get_workflow_response

    # Workflow execution methods

    def create_workflow_execution_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /workflow/execution")
        create_workflow_execution_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/workflow/execution', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return create_workflow_execution_response

    def get_workflow_execution_request(self, id):
        print("GET /workflow/execution/{}".format(id))
        get_workflow_execution_response = requests.get(
            self.stack_resources["WorkflowApiEndpoint"] + '/workflow/execution/' + id, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return get_workflow_execution_response

    def create_terminology_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/translate/create_terminology")
        create_terminology_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/translate/create_terminology', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return create_terminology_response
    
    def get_terminology_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/translate/get_terminology")
        get_terminology_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/translate/get_terminology', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return get_terminology_response

    def create_vocabulary_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/transcribe/create_vocabulary")
        create_vocabulary_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/transcribe/create_vocabulary', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return create_vocabulary_response

    def get_vocabulary_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/transcribe/get_vocabulary")
        get_vocabulary_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/transcribe/get_vocabulary', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)

        return get_vocabulary_response

    def delete_terminology_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/translate/delete_terminology")
        create_terminology_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/translate/delete_terminology', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)
        return create_terminology_response

    def delete_vocabulary_request(self, body):
        headers = {"Content-Type": "application/json"}
        print("POST /service/transcribe/delete_vocabulary")
        create_vocabulary_response = requests.post(
            self.stack_resources["WorkflowApiEndpoint"] + '/service/transcribe/delete_vocabulary', headers=headers, json=body, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)
        return create_vocabulary_response


# Workflow API Fixture


@pytest.fixture(scope='session')
def workflow_api(stack_resources, testing_env_variables):
    def _gen_api():
        testing_api = WorkflowAPI(stack_resources, testing_env_variables)
        return testing_api
    return _gen_api


# Dataplane API Class


class DataplaneAPI:
    def __init__(self, stack_resources, testing_env_variables):
        self.env_vars = testing_env_variables
        self.stack_resources = stack_resources
        self.auth = AWS4Auth(testing_env_variables['ACCESS_KEY'], testing_env_variables['SECRET_KEY'],
                             testing_env_variables['REGION'], 'execute-api',
                             session_token=testing_env_variables.get('SESSION_TOKEN'))

    # Dataplane methods

    def get_single_metadata_field(self, asset_id, operator):
        url = self.stack_resources["DataplaneApiEndpoint"] + \
            'metadata/' + asset_id + "/" + operator
        headers = {"Content-Type": "application/json"}
        print(
            "GET /metadata/{asset}/{operator}".format(asset=asset_id, operator=operator))
        single_metadata_response = requests.get(
            url, headers=headers, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)
        return single_metadata_response

    def delete_asset(self, asset_id):
        url = self.stack_resources["DataplaneApiEndpoint"] + \
            'metadata/' + asset_id
        headers = {"Content-Type": "application/json"}
        print("DELETE /metadata/{asset}".format(asset=asset_id))
        delete_asset_response = requests.delete(
            url, headers=headers, verify=True, auth=self.auth, timeout=REQUEST_TIMEOUT)
        return delete_asset_response

# Dataplane API Fixture


@pytest.fixture(scope='session')
def dataplane_api(stack_resources, testing_env_variables):
    def _gen_api():
        testing_api = DataplaneAPI(stack_resources, testing_env_variables)
        return testing_api
    return _gen_api


@pytest.fixture(scope='session')
def vocabulary(workflow_api, stack_resources, testing_env_variables):
    workflow_api = workflow_api()
    vocabulary_s3_uri = 's3://' + \
        stack_resources['DataplaneBucket'] + '/' + \
        testing_env_variables['SAMPLE_VOCABULARY_FILE']

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    create_vocabulary_body = {
        "vocabulary_name": testing_env_variables['SAMPLE_VOCABULARY_FILE'],
        "language_code": "en-US",
        "s3uri": vocabulary_s3_uri
    }

    # Try deleting the test vocabulary in case the previous test failed prematurely
    delete_vocabulary_body = {
        "vocabulary_name": testing_env_variables['SAMPLE_VOCABULARY_FILE']
    }
    delete_vocabulary_request = workflow_api.delete_vocabulary_request(
        delete_vocabulary_body)
    
    # Create test vocabulary
    create_vocabulary_request = workflow_api.create_vocabulary_request(
        create_vocabulary_body)
    assert create_vocabulary_request.status_code == 200

    # wait for vocabulary to complete

    processing = True

    while processing:
        body = {'vocabulary_name': testing_env_variables['SAMPLE_VOCABULARY_FILE']}
        get_vocabulary_response = workflow_api.get_vocabulary_request(body)

        assert get_vocabulary_response.status_code == 200

        response = get_vocabulary_response.json()

        json.dumps(response)
        status = response["VocabularyState"]

        allowed_statuses = ['PENDING','READY']

        assert status in allowed_statuses

        if status == "READY":
            processing = False
        else:
            print('Sleeping for 30 seconds before retrying')
            time.sleep(30)

    yield create_vocabulary_body
    delete_vocabulary_body = {
        "vocabulary_name": testing_env_variables['SAMPLE_VOCABULARY_FILE']
    }
    delete_vocabulary_request = workflow_api.delete_vocabulary_request(
        delete_vocabulary_body)
    assert delete_vocabulary_request.status_code == 200


@pytest.fixture(scope='session')
def terminology(workflow_api, dataplane_api, stack_resources, testing_env_variables):
    workflow_api = workflow_api()

    create_terminology_body = {
        "terminology_name": "uitestterminology",
        "terminology_csv": "\"en\",\"es\"\n\"STEEN\",\"STEEN-replaced-by-terminology\""
    }

    # Try deleting the test terminology in case the previous test failed prematurely
    delete_terminology_body = {
        "terminology_name": "uitestterminology"
    }
    delete_terminology_request = workflow_api.delete_terminology_request(
        delete_terminology_body)
    
    create_terminology_request = workflow_api.create_terminology_request(
        create_terminology_body)
    assert create_terminology_request.status_code == 200

    # wait for terminology to complete

    processing = True
    retry = 20

    while create_terminology_request.status_code == 200 and processing:
        if retry == 0:
            break
        
        body = {"terminology_name": "uitestterminology"}
        get_terminology_response = workflow_api.get_terminology_request(body)

        if get_terminology_response.status_code == 200:
            processing = False
        else:
            print('Sleeping for 60 seconds before retrying')
            retry = retry - 1
            time.sleep(60)

    yield create_terminology_body
    delete_terminology_body = {
        "terminology_name": "uitestterminology"
    }
    delete_terminology_request = workflow_api.delete_terminology_request(
        delete_terminology_body)
    assert delete_terminology_request.status_code == 200

# Return the workflow configuration.  If all operators is True, run all operators in the workflow.
# If all_operators is False, run only the subtitle workflow
def workflow_config(all_operators):

    # Define the video workflow used as the base for tests
    PreprocessVideo = {
        "Thumbnail": {
            "ThumbnailPosition": "5",
            "Enabled": True
        },
        "Mediainfo": {
            "Enabled": True
        }
    }
    AnalyzeVideo = {
        "faceDetection": {
            "Enabled": all_operators
        },
        "technicalCueDetection": {
            "Enabled": all_operators
        },
        "shotDetection": {
            "Enabled": all_operators
        },
        "celebrityRecognition": {
            "MediaType": "Video",
            "Enabled": all_operators
        },
        "labelDetection" : {
            "MediaType": "Video",
            "Enabled": all_operators
        },
        "personTracking": {
            "MediaType": "Video",
            "Enabled": False
        },
        "faceSearch": {
            "MediaType": "Video",
            "Enabled": False
        },
        "textDetection": {
            "MediaType": "Video",
            "Enabled": all_operators
        },
        "Mediaconvert": {
            "MediaType": "Video",
            "Enabled": False
        },
        "TranscribeVideo": {
            "Enabled": True,
            "TranscribeLanguage": "en-US",
            "MediaType": "Audio"
        }
    }     
    AnalyzeText = {
        "ComprehendEntities": {
            "MediaType": "Text",
            "Enabled": all_operators
        },
        "ComprehendKeyPhrases": {
            "MediaType": "Text",
            "Enabled": all_operators
        }
    }
    
    TransformText = {
        "WebToSRTCaptions": {
            "MediaType": "MetadataOnly",
            "TargetLanguageCodes": [
                "en",
                "es"
                ],
            "SourceLanguageCode": "en",
            "Enabled": True
            },
        "WebToVTTCaptions": {
            "MediaType": "MetadataOnly",
            "TargetLanguageCodes": [
                "en",
                "es"
                ],
            "SourceLanguageCode": "en",
            "Enabled": True
        },
        "PollyWebCaptions": {
            "MediaType":"MetadataOnly",
            "Enabled": True,
            "SourceLanguageCode": "en"
        }
    }
    WebCaptions = {
        "WebCaptions": {
            "MediaType": "MetadataOnly",
            "SourceLanguageCode": "en",
            "Enabled": True,
        }
    }
    Translate = {
        "Translate": {
            "MediaType": "Text",
            "Enabled": False,
        },
        "TranslateWebCaptions": {
            "MediaType":"MetadataOnly",
            "Enabled": True,
            "TargetLanguageCodes": [
                "es"
            ],
            "SourceLanguageCode": "en",
            "ParallelDataNames": []
        }
    }

    workflow = {
        "Name": "ContentLocalizationWorkflow",
    }
    workflow["Configuration"] = {}
    workflow["Configuration"]["PreprocessVideo"] = PreprocessVideo
    workflow["Configuration"]["AnalyzeVideo"] = AnalyzeVideo
    workflow["Configuration"]["TransformText"] = TransformText
    workflow["Configuration"]["WebCaptions"] = WebCaptions
    workflow["Configuration"]["Translate"] = Translate
    workflow["Configuration"]["AnalyzeText"] = AnalyzeText
    return workflow


def execute_workflow(workflow_api,test_workflow_execution):
    # create workflow execution

    workflow_execution_request = workflow_api.create_workflow_execution_request(
        test_workflow_execution)
    assert workflow_execution_request.status_code == 200

    workflow_execution_response = workflow_execution_request.json()
    workflow_execution_id = workflow_execution_response["Id"]
    asset_id = workflow_execution_response["AssetId"]

    time.sleep(5)

    # wait for workflow to complete

    workflow_processing = True

    while workflow_processing:
        get_workflow_execution_request = workflow_api.get_workflow_execution_request(
            workflow_execution_id)
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

    return workflow_execution_request



@pytest.fixture(scope='function')
def workflow_with_customizations(workflow_api, dataplane_api, vocabulary, terminology, stack_resources, testing_env_variables):
    workflow_api = workflow_api()
    dataplane_api = dataplane_api()

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    workflow = workflow_config(False)
    workflow["Configuration"]["AnalyzeVideo"]["TranscribeVideo"]["VocabularyName"] \
        = vocabulary["vocabulary_name"]
    workflow["Configuration"]["Translate"]["TranslateWebCaptions"]["TerminologyNames"] \
        = [{
            "Name": terminology["terminology_name"],
            "TargetLanguageCodes":[
                "es"
                ]
            }
        ]

    workflow["Input"] = {
        "Media": {
            "Video": {
                "S3Bucket": stack_resources['DataplaneBucket'],
                "S3Key": 'upload/' + testing_env_variables['SAMPLE_VIDEO']
            }
        }
    }

    print(json.dumps(workflow))

    if testing_env_variables['USE_EXISTING_WORKFLOW']:
        return {}

    workflow_execution_request = workflow_api.create_workflow_execution_request(
        workflow)
    assert workflow_execution_request.status_code == 200

    # Create a second workflow to avoid having to code 1 vs. many conditions for xpaths
    workflow_execution_request2 = workflow_api.create_workflow_execution_request(
        workflow)
    assert workflow_execution_request2.status_code == 200

    workflow_execution_response = workflow_execution_request.json()
    workflow_execution_id = workflow_execution_response["Id"]
    asset_id = workflow_execution_response["AssetId"]

    time.sleep(5)

    # wait for workflow to complete

    workflow_processing = True

    while workflow_processing:
        get_workflow_execution_request = workflow_api.get_workflow_execution_request(
            workflow_execution_id)
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

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "Mediainfo")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "WebCaptions_en")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "WebCaptions_es")
    assert asset_mediainfo_request.status_code == 200

    print(asset_mediainfo_request.json())

    return workflow_execution_request

@pytest.fixture(scope='function')
def workflow_to_modify(workflow_api, dataplane_api, vocabulary, terminology, stack_resources, testing_env_variables):
    workflow_api = workflow_api()
    dataplane_api = dataplane_api()

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    workflow = workflow_config(True)
    workflow["Input"] = {
        "Media": {
            "Video": {
                "S3Bucket": stack_resources['DataplaneBucket'],
                "S3Key": 'upload/' + testing_env_variables['SAMPLE_VIDEO']
            }
        }
    }

    if testing_env_variables['USE_EXISTING_WORKFLOW']:
        return {}

    workflow_execution_request = workflow_api.create_workflow_execution_request(
        workflow)
    assert workflow_execution_request.status_code == 200

    workflow_execution_response = workflow_execution_request.json()
    workflow_execution_id = workflow_execution_response["Id"]
    asset_id = workflow_execution_response["AssetId"]

    time.sleep(5)

    # wait for workflow to complete

    workflow_processing = True

    while workflow_processing:
        get_workflow_execution_request = workflow_api.get_workflow_execution_request(
            workflow_execution_id)
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

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "Mediainfo")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "WebCaptions_en")
    assert asset_mediainfo_request.status_code == 200

    asset_mediainfo_request = dataplane_api.get_single_metadata_field(
        asset_id, "WebCaptions_es")
    assert asset_mediainfo_request.status_code == 200

    print(asset_mediainfo_request.json())

    return workflow_execution_request


