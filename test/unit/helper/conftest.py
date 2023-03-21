# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import os
import tempfile
import json
from unittest.mock import patch
from botocore.stub import Stubber


@pytest.fixture(autouse=True)
def mock_env_variables(monkeypatch):
    """Mock up environment variables that the testing target depends on"""
    monkeypatch.syspath_prepend('../../source/')
    monkeypatch.setenv("DataplaneBucket", 'testDataplaneBucket')
    monkeypatch.setenv("botoConfig", '{"user_agent_extra": "AwsSolution/SO0164/2.0.4"}')
    monkeypatch.setenv('AWS_XRAY_CONTEXT_MISSING', 'LOG_ERROR')
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test")
    monkeypatch.setenv("SearchEndpoint", "localhost/search")
    monkeypatch.setenv("DataplaneEndpoint", "https://localhost/dataplane/api")
    monkeypatch.setenv("WorkflowEndpoint", "https://localhost/workflow/api")
    monkeypatch.setenv("UserPoolId", "us-west-2_userPoolId")
    monkeypatch.setenv("AwsRegion", "us-west-2")
    monkeypatch.setenv("PoolClientId", "poolClientId")
    monkeypatch.setenv("IdentityPoolId", "us-west2:identityPoolId")


class Context:
    """Fake context that represents the lambda context passed to the lambda handler."""
    log_stream_name = 'testLogStreamName'

    def __str__(self) -> str:
        return "LambdaContext(log_stream_name={})".format(self.log_stream_name)


class FakeResponse:
    """Fake response to return when opening a HTTP request."""
    getcode = 200
    msg = "SUCCESS"


@pytest.fixture
def context(request):
    """Yields an instance of `Context` representing the lambda context.

    If the test case is a class method, a `context` attribute will also
    be set on the object instance so the method can access it via self.context.
    """
    c = Context()
    if request.cls is not None:
        request.cls.context = c
    yield c


@pytest.fixture
def s3_client_stub(request, mock_env_variables):
    """Activate a Stubber for the s3 client used by the target module.

    https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html

    Yields the Stubber instance and also creates an attribute on the test class instance.
    """
    import helper.website_helper as app
    with Stubber(app.s3_client) as stubber:
        if request.cls is not None:
            request.cls.s3_client_stub = stubber
        yield stubber
        # Always assert that no responses are pending in the queue.
        stubber.assert_no_pending_responses()


@pytest.fixture
def s3_resource_stub(request, mock_env_variables):
    """Activate a Stubber for the s3 client associated with the s3 resource in the target.

    Yields the Stubber instance and also creates an attribute on the test class instance.
    """
    import helper.website_helper as app
    with Stubber(app.s3.meta.client) as stubber:
        if request.cls is not None:
            request.cls.s3_resource_stub = stubber
        yield stubber
        # Always assert that no responses are pending in the queue.
        stubber.assert_no_pending_responses()


@pytest.fixture
def build_opener(request, mock_env_variables):
    """Patch the `build_opener` by replacing it with an auto-spec Mock.

    Yields the Mock instance and also creates an attribute on the test class instance.
    """
    with patch('helper.website_helper.build_opener', autospec=True, spec_set=True) as wrapper:
        # Set our fake response as the return value of the `open` method on the instance.
        instance = wrapper.return_value
        instance.open.return_value = FakeResponse()

        if request.cls is not None:
            request.cls.build_opener = wrapper
        yield wrapper

        # Each test case would call `build_opener` and then `open` exactly one time.
        # Make that assertion here so the individual test case doesn't need to do it.
        wrapper.assert_called_once()
        instance.open.assert_called_once()


@pytest.fixture
def send_response(request):
    """Patch the `send_response` function by replacing it with an auto-spec Mock.

    Yields the Mock instance and also creates an attribute on the test class instance.
    """
    with patch('helper.website_helper.send_response', autospec=True, spec_set=True) as wrapper:
        # Make a property on the test class instance that can be accessed via self.send_response
        if request.cls is not None:
            request.cls.send_response = wrapper
        yield wrapper
        wrapper.assert_called_once()


@pytest.fixture
def cwd_temp():
    """Creates a temp directory and makes it the current working directory for a test case.

    Any temporary files written to the directory will get deleted when the test case ends.
    """
    # Create the temporary directory. It will get deleted when the `with` block ends.
    with tempfile.TemporaryDirectory() as tempdir:
        # Save the current working directory so we can reset it at the end
        cwd = os.getcwd()
        # Change to the temp directory
        os.chdir(tempdir)
        # Yield to the test case so it can run
        yield
        # Reset the working directory
        os.chdir(cwd)


@pytest.fixture
def webapp_manifest(cwd_temp):
    """Make a webapp-manifest.json file to be read by the `copy_source` function.

    This fixture depends on the `cwd_temp` fixture, so the file can be created
    in the current working directory. It writes a file at './webapp-manifest.json'
    containing a JSON list of fake files making up the web application.

    After writing the JSON file to the file system, it yields the list of files
    to the test case so the test case can make assertions based on the list.
    """

    # Make up a fake manifest list.
    manifest = [
        "index.html",
        "css/chunk.css",
        "css/app.css",
        "js/chunk.js",
        "js/app.js",
        "img/icons/favicon-16x16.png",
        "runtimeConfig.json",
        "manifest.json",
        "service-worker.js",
        "robots.txt"
    ]

    # Dump the list to the known file name as JSON.
    with open('./webapp-manifest.json', mode='w') as file:
        json.dump(manifest, file)

    # Yield the list to the test case.
    yield manifest


@pytest.fixture(params=["Create", "Update"])
def request_type_copy(request):
    """Yields each request type that causes files to be copied.

    Test cases depending on this fixture will be called once for
    each parameter in the fixture's `params` list.
    i.e., It will result in two test cases for each test case;
    one for "Create" and one for "Update".
    """
    yield request.param
