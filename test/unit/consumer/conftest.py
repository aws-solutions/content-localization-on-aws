# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import glob
import os
from unittest.mock import create_autospec, patch
from botocore.stub import Stubber


@pytest.fixture(autouse=True)
def mock_env_variables(monkeypatch):
    """Mock up environment variables that the testing target depends on"""
    monkeypatch.syspath_prepend('../../source/')
    monkeypatch.setenv("DataplaneBucket", 'testDataplaneBucket')
    monkeypatch.setenv("EsEndpoint", 'testSearchEndpoint')
    monkeypatch.setenv("botoConfig", '{"user_agent_extra": "AwsSolution/SO0164/2.0.4"}')
    monkeypatch.setenv('AWS_XRAY_CONTEXT_MISSING', 'LOG_ERROR')
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test")


@pytest.fixture
def s3_client_stub(mock_env_variables):
    """Activate a Stubber for the s3 client used by the target module.

    https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html

    Yields the Stubber instance.
    """
    import consumer.lambda_handler as app
    with Stubber(app.s3) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def elasticsearch_stub(mock_env_variables):
    """Create auto-spec Mock for `Elasticsearch` and yield the Mock.

    Also, reduce MAC_BULK_INDEX_PAYLOAD_SIZE to 2000000 for testing.
    """
    import consumer.lambda_handler as app
    es = app.Elasticsearch
    bulk_size = app.MAX_BULK_INDEX_PAYLOAD_SIZE
    app.MAX_BULK_INDEX_PAYLOAD_SIZE = 2000000
    wrapper = create_autospec(es)
    app.Elasticsearch = wrapper
    try:
        yield wrapper
    finally:
        app.Elasticsearch = es
        app.MAX_BULK_INDEX_PAYLOAD_SIZE = bulk_size


@pytest.fixture
def index_document_stub():
    """Patch the `index_document` function by replacing it with an auto-spec Mock."""
    with patch('consumer.lambda_handler.index_document', autospec=True, spec_set=True) as stub:
        yield stub


# Find all JSON files under at ./operators/*.json
# The files represent the S3 objects pointed to by the modify operator.
# Any JSON files found in that directory will be assumed to represent a test case.
@pytest.fixture(params=[
    # Just take the base name.
    os.path.basename(p)
    # Look for .json and .json.gz in case we have a large test case that requires compression.
    for ext in ['*.json', '*.json.gz']
    # Find each of the files by joining this source files's directory to the sub-directory.
    for p in glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'operators', ext))
])
def modify_operator_data(request):
    """Finds all data files representing operators and yields a tuple[str, str].

      * The first element of the tuple is the operator name.
      * The second element of the tuple is the full file path of the JSON data file.

    This fixture causes the test case to run once for each operator found.
    """
    # Reconstruct the full path of the file
    full_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'operators', request.param)
    # Trim off the extension (i.e., .json or .json.gz)
    op_name = request.param
    ext = 'ext'
    while ext not in ['.json', '']:
        op_name, ext = os.path.splitext(op_name)
    # return the name of the operator and the full path off the file
    return op_name, full_path
