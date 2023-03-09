# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import base64
import json
import gzip
import os
from botocore.response import StreamingBody
from io import BytesIO
from unittest.mock import call, create_autospec

PARTITION_KEY = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
WORKFLOW_ID = '11111111-2222-3333-4444-555555555555'

# This dict maps an operator to a tuple containing expectations about it:
#   1. The processing function that should be called by the operator.
#   2. A list of additional arguments we expect to be passed to the function.
#   3. The number of times we expect `bulk_index` to get called.
#   4. The number of times we expect `index_document` to get called.
OP_TO_PROC_FUNC = {
    "transcribevideo": ("process_transcribe", ["video"], 1, 1),
    "transcribeaudio": ("process_transcribe", ["audio"], 1, 1),
    "translate": ("process_translate", [], 0, 1),
    "webcaptions_es": ("process_webcaptions", ['es'], 0, 1),
    "webcaptions_en": ("process_webcaptions", ['en'], 0, 1),
    "mediainfo": ("process_mediainfo", [], 1, 0),
    "genericdatalookup": ("process_generic_data", [], 1, 0),
    "labeldetection": ("process_label_detection", [], 2, 0),
    "celebrityrecognition": ("process_celebrity_detection", [], 1, 0),
    "contentmoderation": ("process_content_moderation", [], 1, 0),
    "facedetection": ("process_face_detection", [], 1, 0),
    "face_search": ("process_face_search", [], 1, 0),
    "entities": ("process_entities", [], 1, 0),
    "key_phrases": ("process_keyphrases", [], 1, 0),
    "textdetection": ("process_text_detection", [], 1, 0),
    "shotdetection": ("process_shot_detection", [], 1, 0),
    "technicalcuedetection": ("process_technical_cue_detection", [], 1, 0)
}


class TestIndexDocument:
    """Tests for `index_document`.

    We separate these to work around the Elasticsearch.index method, which has
    a dynamic signature and would otherwise cause test cases to fail due to the
    auto-spec parameter validation checks.
    """

    def test_index_document_success(self):
        import consumer.lambda_handler as lambda_function

        # Set up mock for index_document function
        es_stub = create_autospec(FakeElasticsearch)
        es_object = es_stub()

        # Call index_document
        lambda_function.index_document(es_object, "assetid", "Index", {'Workflow': 'WF', 'Operator': 'OP'})

        # Check that Elasticsearch.index was called
        es_object.index.assert_called_once_with("mieindex", {'Workflow': 'WF', 'Operator': 'OP', "AssetId": "assetid"}, request_timeout=30)

    def test_index_document_fail(self):
        import consumer.lambda_handler as lambda_function

        # Set up mock for index_document function
        es_stub = create_autospec(FakeElasticsearch)
        es_object = es_stub()

        # Make Elasticsearch.index raise an exception
        es_object.index.side_effect = Exception("Fake exception")

        # Call index_document
        lambda_function.index_document(es_object, "assetid", "Index", {'Workflow': 'WF', 'Operator': 'OP'})

        # Check that Elasticsearch.index was called
        es_object.index.assert_called_once_with("mieindex", {'Workflow': 'WF', 'Operator': 'OP', "AssetId": "assetid"}, request_timeout=30)


@pytest.mark.usefixtures("s3_client_stub")
class TestError:
    """Do some negative testing to check error conditions."""

    def test_bad_event_input(self):
        import consumer.lambda_handler as lambda_function

        event = None
        with pytest.raises(TypeError) as excinfo:
            lambda_function.lambda_handler(event, make_context())

        assert str(excinfo.value) == "'NoneType' object is not subscriptable"

    def test_missing_kinesis_partition_key(self):
        import consumer.lambda_handler as lambda_function

        event = {"Records": [{"kinesis": {}}]}
        lambda_function.lambda_handler(event, make_context())

    def test_missing_action(self):
        import consumer.lambda_handler as lambda_function

        event = make_event({})
        context = make_context()

        lambda_function.lambda_handler(event, context)


@pytest.mark.usefixtures("s3_client_stub")
class TestInsert:
    """Test INSERT action."""

    def test_insert(self, elasticsearch_stub):
        import consumer.lambda_handler as lambda_function

        event = make_insert_event()
        context = make_context()

        lambda_function.lambda_handler(event, context)

        calls = [
            call().bulk(
                index='mieinitialization',
                body='{"index": {"_index": "mieinitialization", "_type": "_doc"}}\n{"filename": "sample-video.mp4", "created": "1677875460.691329", "AssetId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}'
            )
        ]
        elasticsearch_stub.assert_has_calls(calls)

    def test_insert_missing_payload_key(self, elasticsearch_stub):
        import consumer.lambda_handler as lambda_function

        record = make_insert_record_data()
        # Remove important key from the record
        del record["S3Key"]
        event = make_event(record)
        context = make_context()

        lambda_function.lambda_handler(event, context)

        assert not elasticsearch_stub.called


@pytest.mark.usefixtures("s3_client_stub")
class TestRemove:
    """Test REMOVE action."""

    def test_remove_all(self, elasticsearch_stub):
        import consumer.lambda_handler as lambda_function

        event = make_event({"Action": "REMOVE"})
        context = make_context()

        lambda_function.lambda_handler(event, context)

        elasticsearch_stub.assert_called_once()
        print(elasticsearch_stub.method_calls)

    def test_remove_operator(self, elasticsearch_stub):
        import consumer.lambda_handler as lambda_function

        event = make_event({"Action": "REMOVE", "Operator": "Mediainfo"})
        context = make_context()

        lambda_function.lambda_handler(event, context)

        assert not elasticsearch_stub.called


class TestModify:
    """Test MODIFY action."""

    def test_unsupported_operator(self, s3_client_stub, elasticsearch_stub, index_document_stub):
        import consumer.lambda_handler as lambda_function

        event = make_modify_event('TranslateWebCaptions', s3_client_stub)
        context = make_context()

        lambda_function.lambda_handler(event, context)

        assert not elasticsearch_stub.called
        assert not index_document_stub.called

    def test_missing_required_payload_key(self, s3_client_stub, elasticsearch_stub, index_document_stub):
        import consumer.lambda_handler as lambda_function

        event = make_modify_event(None, None)
        context = make_context()

        lambda_function.lambda_handler(event, context)

        assert not elasticsearch_stub.called
        assert not index_document_stub.called

    def test_missing_metadata_file(self, s3_client_stub, elasticsearch_stub, index_document_stub):
        import consumer.lambda_handler as lambda_function

        event = make_modify_event('TranslateWebCaptions', s3_client_stub, data=None)
        context = make_context()

        lambda_function.lambda_handler(event, context)

        assert not elasticsearch_stub.called
        assert not index_document_stub.called

    def test_supported_operator(self, s3_client_stub, elasticsearch_stub, index_document_stub, modify_operator_data):
        """Test each of the supported operators. This test is called once for each operator.

        Args:
            modify_operator_data: This fixture causes the test case to become multiple test case
                (one for each operator). This method is called once for each operator. For each
                call, this argument contains a tuple[str, str] representing the operator name
                and the absolute path to the JSON file, respectively.
        """
        import consumer.lambda_handler as lambda_function

        # Get the operator name and the data file path
        operator, file_path = modify_operator_data
        # Look up the operator in the map so we know the expectations
        process_func, added_params, bulk_call_count, index_doc_call_count = OP_TO_PROC_FUNC[operator.lower()]

        # Read the contents of the file so we can set up the event.
        if os.path.splitext(file_path)[1] == '.gz':
            with gzip.open(file_path) as f:
                data = EncodedData(f.read())
        else:
            with open(file_path) as f:
                data = EncodedData(f.read())

        # Make the event. (This will also add a "get_object" response to the S3 client stub.)
        event = make_modify_event(operator, s3_client_stub, data=data)
        context = make_context()

        # Create a Mock for the processing function so we can capture the function
        # calls. The Mock will pass through the call to the original function but
        # it will track the call so we can make assertions.
        with ProcessOperatorStubber(lambda_function, operator, process_func) as op_stubber:
            # Act - Run the lambda handler.
            lambda_function.lambda_handler(event, context)
            # Assert that our processing function was called with the expected arguments.
            op_stubber.stub.assert_called_once_with(PARTITION_KEY, WORKFLOW_ID, str(data), *added_params)

        # Elasticsearch should have been called exactly once.
        # bulk_index and index_document should be called the expected number of times.
        elasticsearch_stub.assert_called_once()
        assert len(elasticsearch_stub.method_calls) == bulk_call_count
        assert index_document_stub.call_count == index_doc_call_count


###############################################################################
# Helper Functions ############################################################


def make_context():
    # The handler doesn't use the context so None is fine.
    return None


def make_modify_event(operator, s3_client_stub, data={}):
    """Make a MODIFY event with the provided data.

    Args:
        s3_client_stub: Stubber for s3_client. If not `None`, a response will be
            added to the s3_client_stub based on the value of `data`.
        data: If `None`, an error will be queued up in `s3_client_stub` instead
            of a success response. Otherwise, a success response will be added
            with the body containing `data`.
    """
    return make_event(make_modify_record_data(operator, s3_client_stub, data))


def make_insert_event():
    """Make a INSERT event."""
    return make_event(make_insert_record_data())


def make_event(*data):
    """Make an event with a list of records.

    Args:
        data: list of data to encode into a record structure.
    """
    return {
        'Records': [
            make_record(d)
            for d in data
        ]
    }


def make_record(data):
    """Make a record with record['kinesis']['data'] set to encoded data.

    Args:
        data: The data to be contained within the record. It will be encoded.
    """
    record = {
        'kinesis': {
            'kinesisSchemaVersion': '1.0',
            'partitionKey': PARTITION_KEY,
            'sequenceNumber': '55555555555555555555555555555555555555555555555555555555',
            'data': encode_data(data),
            'approximateArrivalTimestamp': 1677877863.133
        },
        'eventSource': 'aws:kinesis',
        'eventVersion': '1.0',
        'eventID': 'shardId-000000000000:55555555555555555555555555555555555555555555555555555555',
        'eventName': 'aws:kinesis:record',
        'invokeIdentityArn': 'arn:aws:iam::123456789012:role/teststack-OpensearchStack-StreamConsumerRole',
        'awsRegion': 'us-west-2',
        'eventSourceARN': 'arn:aws:kinesis:us-west-2:123456789012:stream/teststack-MieStack-Analytics-AnalyticsStream'
    }
    return record


def encode_data(data) -> str:
    """Encode the `data` into a format expected by the kinesis record.

    A structure will get serialized to JSON, then encoded as UTF-8, then
    base64 encoded, then finally converted to a str.
    """
    return str(EncodedData(base64.b64encode(EncodedData(data).bytes)))


def make_insert_record_data():
    return {
        'S3Bucket': os.environ['DataplaneBucket'],
        'S3Key': 'upload/sample-video.mp4',
        'MediaType': 'Video',
        'Created': '1677875460.691329',
        'Action': 'INSERT'
    }


def make_modify_record_data(operator, s3_client_stub, response_body):
    """Make a MODIFY record and set up S3 response.

    Args:
        s3_client_stub: Stubber for s3_client. If not `None`, a response will be
            added to the s3_client_stub based on the value of `response_body`.
        response_body: If `None`, an error will be queued up in `s3_client_stub`
            instead of a success response. Otherwise, a success response will be
            added with the body containing `response_body`.
    """
    partition = PARTITION_KEY
    workflow = WORKFLOW_ID
    pointer = 'private/assets/{}/workflows/{}/{}.json'.format(partition, workflow, operator)

    if s3_client_stub is not None:
        if response_body is None:
            # Make the S3 client return an error.
            s3_client_stub.add_client_error('get_object')
        else:
            # Encode the response body and queue up a get_object response.
            body = EncodedData(response_body).bytes
            s3_client_stub.add_response(
                'get_object',
                expected_params={
                    'Bucket': os.environ['DataplaneBucket'],
                    'Key': pointer
                },
                service_response={
                    'Body': StreamingBody(BytesIO(body), len(body))
                }
            )

    # Create the record data
    record = {
        'Action': 'MODIFY',
        'Pointer': pointer,
        'Workflow': workflow
    }

    # Only add an operator if the operator is not None
    if operator is not None:
        record['Operator'] = operator

    return record


class ProcessOperatorStubber:
    """Stub out a processing function by wrapping it in a Mock.

    This supports the `with` keyword for automatic clean-up.
    """

    def __init__(self, module, operator, process_function):
        # Store the important information so we can swap out with the Mock.
        self._module = module
        self._operator = operator
        self._process_function = process_function
        # Get the original processing function
        self._func = getattr(self._module, self._process_function)

        # Create the auto-spec Mock for the function.
        self.stub = create_autospec(self._func)
        self.stub.wraps = self._func

        # The side_effect of the Mock is the original function so any call
        # to the Mock gets passed on to the original function. The Mock
        # allows us to verify that the input arguments are valid and to
        # make assertions about the function calls.
        self.stub.side_effect = self._func

    def __enter__(self):
        # Replace the original function with the Mock.
        setattr(self._module, self._process_function, self.stub)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # Replace the Mock with the original function.
        setattr(self._module, self._process_function, self._func)


class EncodedData:
    """Encodes data into bytes."""

    def __init__(self, data):
        # If data is a dict, dump it to a JSON string.
        if isinstance(data, dict):
            data = json.dumps(data)

        # If data is a string, encode it to bytes.
        if isinstance(data, str):
            data = data.encode('utf-8')

        # If data is bytes, it's what we want; just store it.
        if isinstance(data, bytes):
            self.bytes = data
        elif isinstance(data, EncodedData):
            # If data is a EncodedData instance, just copy bytes.
            self.bytes = data.bytes
        else:
            # Not supported object.
            assert False

    def __str__(self):
        """Return a str representation of the encoded data."""
        return self.bytes.decode('utf-8')


class FakeElasticsearch:
    """Fake Elasticsearch that has a method with the expected signature.

    This allows us to work around the auto-spec parameter validation checks
    that would otherwise fail due to the dynamic signature in the real
    implementation of the `index` method. It uses a decorator that allows
    for additional parameters/arguments that aren't in the static signature.
    """

    def index(self, index, body, request_timeout=None):
        """Does nothing. We will wrap it in an auto-spec Mock."""
        pass
