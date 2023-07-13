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

from elasticsearch import Elasticsearch, RequestsHttpConnection
import base64
import json
import os
from botocore import config
import boto3
from requests_aws4auth import AWS4Auth

mie_config = json.loads(os.environ['botoConfig'])
config = config.Config(**mie_config)

MAX_BULK_INDEX_PAYLOAD_SIZE = 5000000
es_endpoint = os.environ['EsEndpoint']
dataplane_bucket = os.environ['DataplaneBucket']

s3 = boto3.client('s3', config=config)


def normalize_confidence(confidence_value):
    converted = float(confidence_value) * 100
    return str(converted)


def convert_to_milliseconds(time_value):
    converted = float(time_value) * 1000
    return str(converted)


def print_key_error(e: KeyError, item: dict):
    print("KeyError: " + str(e))
    print("Item: " + json.dumps(item))


def print_unable_to_load_data_into_es(e: Exception, data: dict):
    print('Unable to load data into es:', e)
    print("Data: ", data)


def process_text_detection(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # We can tell if json results are paged by checking to see if the json results are an instance of the list type.
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    # handle paged results
    for item in (item for page in metadata for item in page["TextDetections"]):
        try:
            # Handle text detection schema for videos
            if "TextDetection" in item:
                text_detection = item["TextDetection"]
                text_detection["Timestamp"] = item["Timestamp"]
                # Flatten the bbox Label array
                text_detection["BoundingBox"] = text_detection["Geometry"]["BoundingBox"]
                del text_detection["Geometry"]
            # Handle text detection schema for images
            else:
                text_detection = item

            text_detection["Operator"] = "textDetection"
            text_detection["Workflow"] = workflow
            print(text_detection)
            extracted_items.append(text_detection)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "textDetection", extracted_items)


def process_celebrity_detection(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    for item in (item for page in metadata for item in page.get("Celebrities", []) + page.get("CelebrityFaces", [])):
        try:
            item["Operator"] = "celebrity_detection"
            item["Workflow"] = workflow

            # Parse schema for videos:
            # https://docs.aws.amazon.com/rekognition/latest/dg/celebrities-video-sqs.html
            if "Celebrity" in item:
                # flatten the inner Celebrity array
                item["Name"] = item["Celebrity"]["Name"]
                item["Confidence"] = item["Celebrity"]["Confidence"]
                # Bounding box can be around body or face. Prefer body.
                bounding_box = item["Celebrity"].get("Face", {}).get("BoundingBox", '')
                bounding_box = item["Celebrity"].get("BoundingBox", bounding_box)
                item["BoundingBox"] = bounding_box
                # Set IMDB URL if it exists.
                url = item["Celebrity"].get("Urls", [''])[0]
                item['URL'] = url
                # delete flattened array
                del item["Celebrity"]

            # Parse schema for images:
            # https://docs.aws.amazon.com/rekognition/latest/dg/celebrities-procedure-image.html
            if "Face" in item:
                # flatten the inner Face array
                item["Confidence"] = item["Face"]["Confidence"]
                item["BoundingBox"] = item["Face"]["BoundingBox"]
                # delete flattened array
                del item["Face"]

            extracted_items.append(item)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "celebrity_detection", extracted_items)


def process_content_moderation(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    for page in metadata:
        for item in page.get("ModerationLabels", []):
            try:
                item["Operator"] = "content_moderation"
                item["Workflow"] = workflow
                if "ModerationLabel" in item:
                    # flatten the inner ModerationLabel array
                    item["Name"] = item["ModerationLabel"]["Name"]
                    item["ParentName"] = item["ModerationLabel"].get("ParentName", '')
                    item["Confidence"] = item["ModerationLabel"].get("Confidence", '')
                    # Delete the flattened array
                    del item["ModerationLabel"]
                extracted_items.append(item)
            except KeyError as e:
                print_key_error(e, item)
    bulk_index(es, asset, "content_moderation", extracted_items)


def process_face_search(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)

    extracted_items = []
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    for item in (item for page in metadata for item in page.get("Persons", [])):
        item["Operator"] = "face_search"
        item["Workflow"] = workflow
        # flatten person key
        item["PersonIndex"] = item["Person"]["Index"]
        if "BoundingBox" in item["Person"]:
            item["PersonBoundingBox"] = item["Person"]["BoundingBox"]
        # flatten face key
        if "Face" in item["Person"]:
            item["FaceBoundingBox"] = item["Person"]["Face"]["BoundingBox"]
            item["FaceLandmarks"] = item["Person"]["Face"]["Landmarks"]
            item["FacePose"] = item["Person"]["Face"]["Pose"]
            item["FaceQuality"] = item["Person"]["Face"]["Quality"]
            confidence = item["Person"]["Face"]["Confidence"]
            item["Confidence"] = confidence

        if "FaceMatches" in item:
            item["ContainsKnownFace"] = True
            # flatten face matches key
            for face in item["FaceMatches"]:
                item["KnownFaceSimilarity"] = face["Similarity"]
                item["MatchingKnownFaceId"] = face["Face"]["FaceId"]
                item["KnownFaceBoundingBox"] = face["Face"]["BoundingBox"]
                item["ImageId"] = face["Face"]["ImageId"]
            del item["FaceMatches"]
        else:
            item["ContainsKnownFace"] = False
        del item["Person"]

        extracted_items.append(item)

    bulk_index(es, asset, "face_search", extracted_items)


def process_face_detection(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    for page in metadata:
        # Parse schema for video:
        for item in page.get("Faces", []):
            try:
                item["Operator"] = "face_detection"
                item["Workflow"] = workflow
                if "Face" in item:
                    # flatten the inner Face array
                    item["BoundingBox"] = item["Face"]["BoundingBox"]
                    item["AgeRange"] = item["Face"]["AgeRange"]
                    item["Smile"] = item["Face"]["Smile"]
                    item["Eyeglasses"] = item["Face"]["Eyeglasses"]
                    item["Sunglasses"] = item["Face"]["Sunglasses"]
                    item["Gender"] = item["Face"]["Gender"]
                    item["Beard"] = item["Face"]["Beard"]
                    item["Mustache"] = item["Face"]["Mustache"]
                    item["EyesOpen"] = item["Face"]["EyesOpen"]
                    item["MouthOpen"] = item["Face"]["MouthOpen"]
                    item["Emotions"] = item["Face"]["Emotions"]
                    item["Confidence"] = item["Face"]["Confidence"]
                    # Delete the flattened array
                    del item["Face"]
                extracted_items.append(item)
            except KeyError as e:
                print_key_error(e, item)
        # Parse schema for images:
        for item in page.get("FaceDetails", []):
            item["Operator"] = "face_detection"
            item["Workflow"] = workflow
            extracted_items.append(item)
    bulk_index(es, asset, "face_detection", extracted_items)


def process_mediainfo(asset, workflow, results):
    # This function puts mediainfo data in Elasticsearch.
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # Objects in arrays are not well supported by Elastic, so we flatten the tracks array here.
    if isinstance(metadata['tracks'], list):
        for item in metadata['tracks']:
            item["Operator"] = "mediainfo"
            item["Workflow"] = workflow
            extracted_items.append(item)
    bulk_index(es, asset, "mediainfo", extracted_items)


def process_generic_data(asset, workflow, results):
    # This function puts generic data in Elasticsearch.
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # We can tell if json results are paged by checking to see if the json results are an instance of the list type.
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    # handle paged results
    for item in (item for page in metadata for item in page.get("Labels", [])):
        try:
            item["Operator"] = "generic_data_lookup"
            item["Workflow"] = workflow
            if "Label" in item:
                # Flatten the inner Label array
                item["Confidence"] = float(item["Label"]["Confidence"]) * 100
                item["Name"] = item["Label"]["Name"]
                item["Instances"] = ''
                if 'Instances' in item["Label"]:
                    for box in item["Label"]["Instances"]:
                        box["BoundingBox"]["Height"] = float(box["BoundingBox"]["Height"]) / 720
                        box["BoundingBox"]["Top"] = float(box["BoundingBox"]["Top"]) / 720
                        box["BoundingBox"]["Left"] = float(box["BoundingBox"]["Left"]) / 1280
                        box["BoundingBox"]["Width"] = float(box["BoundingBox"]["Width"]) / 1280
                        box["Confidence"] = float(box["Confidence"]) * 100
                    item["Instances"] = item["Label"]["Instances"]
                item["Parents"] = item["Label"].get("Parents", '')
                # Delete the flattened array
                del item["Label"]
            extracted_items.append(item)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "labels", extracted_items)


def process_label_detection(asset, workflow, results):
    # Rekognition label detection puts labels on an inner array in its JSON result, but for ease of search in Elasticsearch we need those results as a top level json array. So this function does that.
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # We can tell if json results are paged by checking to see if the json results are an instance of the list type.
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    # handle paged results
    for item in (item for page in metadata for item in page.get("Labels", [])):
        try:
            item["Operator"] = "label_detection"
            item["Workflow"] = workflow
            if "Label" in item:
                # Flatten the inner Label array
                item["Confidence"] = item["Label"]["Confidence"]
                item["Name"] = item["Label"]["Name"]
                item["Instances"] = item["Label"].get("Instances", '')
                item["Parents"] = item["Label"].get("Parents", '')
                # Delete the flattened array
                del item["Label"]
            extracted_items.append(item)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "labels", extracted_items)


def process_technical_cue_detection(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # We can tell if json results are paged by checking to see if the json results are an instance of the list type.
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    # handle paged results
    for item in (item for page in metadata for item in page.get("Segments", [])):
        try:
            item["Operator"] = "technical_cue_detection"
            item["Workflow"] = workflow
            if "TechnicalCueSegment" in item:
                item["Confidence"] = item["TechnicalCueSegment"]["Confidence"]
                item["Type"] = item["TechnicalCueSegment"]["Type"]

                del item["TechnicalCueSegment"]

                item["StartTimestamp"] = item["StartTimestampMillis"]
                item["EndTimestamp"] = item["EndTimestampMillis"]

                del item["StartTimestampMillis"]
                del item["EndTimestampMillis"]
            extracted_items.append(item)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "technical_cues", extracted_items)


def process_shot_detection(asset, workflow, results):
    metadata = json.loads(results)
    es = connect_es(es_endpoint)
    extracted_items = []
    # We can tell if json results are paged by checking to see if the json results are an instance of the list type.
    if not isinstance(metadata, list):
        # Make it a single page list
        metadata = [metadata]

    # handle paged results
    for item in (item for page in metadata for item in page.get("Segments", [])):
        try:
            item["Operator"] = "shot_detection"
            item["Workflow"] = workflow
            if "ShotSegment" in item:
                item["Confidence"] = item["ShotSegment"]["Confidence"]
                item["Index"] = item["ShotSegment"]["Index"]

                del item["ShotSegment"]

                item["StartTimestamp"] = item["StartTimestampMillis"]
                item["EndTimestamp"] = item["EndTimestampMillis"]

                del item["StartTimestampMillis"]
                del item["EndTimestampMillis"]
            extracted_items.append(item)
        except KeyError as e:
            print_key_error(e, item)
    bulk_index(es, asset, "shots", extracted_items)


def process_translate(asset, workflow, results):
    metadata = json.loads(results)

    translation = metadata
    translation["workflow"] = workflow
    es = connect_es(es_endpoint)
    index_document(es, asset, "translation", translation)


def process_webcaptions(asset, workflow, results, language_code):
    metadata = json.loads(results)
    metadata_type = "webcaptions" + "_" + language_code

    webcaptions = metadata
    webcaptions["Workflow"] = workflow
    webcaptions["Operator"] = metadata_type
    es = connect_es(es_endpoint)
    index_document(es, asset, metadata_type, webcaptions)


def process_transcribe(asset, workflow, results, media_type):
    metadata = json.loads(results)

    transcript = metadata["results"]["transcripts"][0]
    transcript["workflow"] = workflow
    transcript_time = metadata["results"]["items"]

    index_name = media_type + "transcript"
    es = connect_es(es_endpoint)
    index_document(es, asset, index_name, transcript)

    transcribe_items = []

    for item in transcript_time:
        content = item["alternatives"][0]["content"]
        confidence = normalize_confidence(item["alternatives"][0]["confidence"])
        if "start_time" in item and "end_time" in item:
            start_time = convert_to_milliseconds(item["start_time"])
            end_time = convert_to_milliseconds(item["end_time"])
            item["start_time"] = start_time
            item["end_time"] = end_time

        del item["alternatives"]

        item["confidence"] = confidence
        item["content"] = content
        item["Workflow"] = workflow
        item["Operator"] = "transcribe"

        transcribe_items.append(item)

    bulk_index(es, asset, index_name, transcribe_items)


def process_entities(asset, workflow, results):
    metadata = json.loads(results)
    entity_metadata = json.loads(metadata["Results"][0])
    entities = entity_metadata["Entities"]

    es = connect_es(es_endpoint)

    formatted_entities = []

    for entity in entities:
        entity["EntityType"] = entity["Type"]
        entity["EntityText"] = entity["Text"]

        confidence = normalize_confidence(entity["Score"])
        entity["Confidence"] = confidence

        entity["Workflow"] = workflow
        entity["Operator"] = "entities"

        del entity["Type"]
        del entity["Text"]
        del entity["Score"]

        formatted_entities.append(entity)

    bulk_index(es, asset, "entities", formatted_entities)


def process_keyphrases(asset, workflow, results):
    metadata = json.loads(results)
    phrases_metadata = json.loads(metadata["Results"][0])
    phrases = phrases_metadata["KeyPhrases"]

    es = connect_es(es_endpoint)

    formatted_phrases = []

    for phrase in phrases:
        phrase["PhraseText"] = phrase["Text"]

        confidence = normalize_confidence(phrase["Score"])
        phrase["Confidence"] = confidence

        phrase["Workflow"] = workflow
        phrase["Operator"] = "key_phrases"

        del phrase["Text"]
        del phrase["Score"]

        formatted_phrases.append(phrase)

    bulk_index(es, asset, "key_phrases", formatted_phrases)


def process_initialization(asset, results):
    es = connect_es(es_endpoint)
    bulk_index(es, asset, "initialization", [results])


def connect_es(endpoint):
    # Handle aws auth for es# Create a config

    session = boto3.Session()
    credentials = session.get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, session.region_name, 'es',
                       session_token=credentials.token)
    print('Connecting to the ES Endpoint: {endpoint}'.format(endpoint=endpoint))
    try:
        es_client = Elasticsearch(
            hosts=[{'host': endpoint, 'port': 443}],
            use_ssl=True,
            verify_certs=True,
            http_auth=awsauth,
            connection_class=RequestsHttpConnection)
    except Exception as e:
        print("Unable to connect to {endpoint}:".format(endpoint=endpoint), e)
    else:
        print('Connected to elasticsearch')
        return es_client


def delete_asset_all_indices(es_object, asset_id):
    delete_query = {
        "query": {
            "match": {
                "AssetId": asset_id
            }
        }
    }

    try:
        delete_request = es_object.delete_by_query(
            index="_all",
            body=delete_query
        )
    except Exception as e:
        print("Unable to delete from elasticsearch: {es}:".format(es=e)) # nosec - not a SQL statement
    else:
        print(delete_request)
        print("Deleted asset: {asset} from elasticsearch".format(asset=asset_id))


def bulk_index(es_object, asset, index, data):
    if len(data) == 0:
        print("Data is empty. Skipping insert to Elasticsearch.")
        return
    es_index = "mie{index}".format(index=index).lower()
    actions_to_send = []
    # Elasticsearch will respond with an error like, "Request size exceeded 10485760 bytes"
    # if the bulk insert exceeds a maximum payload size. To avoid that, we use a max payload
    # size that is well below the "Maximum Size of HTTP Request Payloads" for the smallest AWS
    # Elasticsearch instance type (10MB). See service limits here:
    # https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/aes-limits.html
    max_payload_size = MAX_BULK_INDEX_PAYLOAD_SIZE
    for item in data:
        item["AssetId"] = asset
        action = json.dumps({"index": {"_index": es_index, "_type": "_doc"}})
        doc = json.dumps(item)
        if ((len('\n'.join(actions_to_send)) + len(action) + len(doc)) < max_payload_size):
            actions_to_send.append(action)
            actions_to_send.append(doc)
        else:
            # send and reset payload before appending the current item
            actions = '\n'.join(actions_to_send)
            print("bulk insert payload size: " + str(len(actions)))
            try:
                es_object.bulk(
                    index=es_index,
                    body=actions
                )
            except Exception as e:
                print_unable_to_load_data_into_es(e, item)
            else:
                print("Successfully stored data in elasticsearch for asset: ", asset)
            # now reset the payload and append the current item
            actions_to_send = []
            actions_to_send.append(action)
            actions_to_send.append(doc)
    # finally send the last item
    print("sending final bulk insert")
    actions = '\n'.join(actions_to_send)
    try:
        es_object.bulk(
            index=es_index,
            body=actions
        )
    except Exception as e:
        print_unable_to_load_data_into_es(e, data)
    else:
        print("Successfully stored data in elasticsearch for asset: ", asset)


def index_document(es_object, asset, index, data):
    es_index = "mie{index}".format(index=index).lower()
    data["AssetId"] = asset
    try:
        es_object.index(
            index=es_index,
            body=data,
            request_timeout=30
        )
    except Exception as e:
        print_unable_to_load_data_into_es(e, data)
    else:
        print("Successfully stored data in elasticsearch for:", asset)


def read_json_from_s3(key):
    bucket = dataplane_bucket
    try:
        obj = s3.get_object(
            Bucket=bucket,
            Key=key
        )
    except Exception as e:
        return {"Status": "Error", "Error": e}
    else:
        results = obj['Body'].read().decode('utf-8')
        return {"Status": "Success", "Results": results}


def lambda_handler(event, _context):
    print("Received event:", event)

    action = None
    asset_id = None
    payload = None

    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        try:
            asset_id = record['kinesis']['partitionKey']
            payload = json.loads(base64.b64decode(record["kinesis"]["data"]))
        except Exception as e:
            print("Error decoding kinesis event", e)
        else:
            print("Decoded payload for asset:", asset_id)
            try:
                action = payload['Action']
            except KeyError as e:
                print("Missing action type from kinesis record:", e)
            else:
                print("Attempting the following action:", action)

        if action is None:
            print("Unable to determine action type")
        elif action == "INSERT":
            handle_insert(asset_id, payload)
        elif action == "MODIFY":
            handle_modify(asset_id, payload)
        elif action == "REMOVE":
            handle_remove(asset_id, payload)


def handle_insert(asset_id, payload):
    # The initial insert action will contain the filename and timestamp.
    # Persist the filename and timestamp to Elasticsearch so users can find
    # assets by searching those fields.
    try:
        # Get filename and timestamp from the payload of the stream message
        s3_key = payload['S3Key']
        filename = s3_key.split("/")[-1]
        created = payload['Created']
        extracted_items = []
        metadata = {"filename": filename, "created": created}
        extracted_items.append(metadata)
        # Save the filename and timestamp to Elasticsearch
        process_initialization(asset_id, metadata)
    except KeyError as e:
        print("Missing required keys in kinesis payload:", e)


def handle_modify(asset_id, payload):
    try:
        operator = payload['Operator']
        s3_pointer = payload['Pointer']
        workflow = payload['Workflow']
    except KeyError as e:
        print("Missing required keys in kinesis payload:", e)
    else:
        # Read in json metadata from s3
        metadata = read_json_from_s3(s3_pointer)
        if metadata["Status"] == "Success":
            process_modify_metadata(asset_id, workflow, operator, metadata)
        else:
            print("Unable to read metadata from s3: {e}".format(e=metadata["Error"]))


def process_modify_metadata(asset_id, workflow, operator, metadata):
    print("Retrieved {operator} metadata from s3, inserting into Elasticsearch".format(operator=operator))
    operator = operator.lower()
    additional_arg = []

    # webcaptions operators are processed the same, but they have a language extension
    # in the operator name.  Strip that off now.  Any language is supported for search
    if operator.startswith("webcaptions_"):
        print("Got webcaptions operator {}".format(operator))
        (operator, language_code) = operator.split("_")
        additional_arg = [language_code]

    # process_transcribe needs to distinguish between video and audio
    elif operator == "transcribevideo":
        additional_arg = ["video"]
    elif operator == "transcribeaudio":
        additional_arg = ["audio"]

    # Route event to process method based on the operator type in the event.
    # These names are the lowercase version of OPERATOR_NAME defined in /source/operators/operator-library.yaml
    def process_unsupported(*args):
        print("We do not store {operator} results".format(operator=operator))

    processing_functions = {
        "transcribevideo": process_transcribe,
        "transcribeaudio": process_transcribe,
        "translate": process_translate,
        "webcaptions": process_webcaptions,
        "mediainfo": process_mediainfo,
        "genericdatalookup": process_generic_data,
        "labeldetection": process_label_detection,
        "celebrityrecognition": process_celebrity_detection,
        "contentmoderation": process_content_moderation,
        "facedetection": process_face_detection,
        "face_search": process_face_search,
        "entities": process_entities,
        "key_phrases": process_keyphrases,
        "textdetection": process_text_detection,
        "shotdetection": process_shot_detection,
        "technicalcuedetection": process_technical_cue_detection,
    }

    process_function = processing_functions.get(operator, process_unsupported)
    process_function(asset_id, workflow, metadata["Results"], *additional_arg)


def handle_remove(asset_id, payload):
    if 'Operator' not in payload:
        print("Operator type not present in payload, this must be a request to delete the entire asset")
        es = connect_es(es_endpoint)
        delete_asset_all_indices(es, asset_id)
    else:
        print(payload)
        print('Not allowing deletion of specific metadata from ES as that is not exposed in the UI')
