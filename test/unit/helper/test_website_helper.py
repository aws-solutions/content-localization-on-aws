# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from botocore.stub import ANY


@pytest.mark.usefixtures("build_opener", "context")
class TestSendResponse:
    """Test the `send_response` function, which uses `build_opener`."""

    def test_send_response(self):
        import helper.website_helper as lambda_function

        # Arrange
        event = make_event("Test")

        # Act
        lambda_function.send_response(event, self.context, "SUCCESS", {"Message": "test message"})

        # The build_opener fixture make assertions for us to ensure
        # we got the expected function calls.


@pytest.mark.usefixtures("s3_client_stub", "s3_resource_stub", "send_response", "context")
class TestLambdaHandler:
    """Test cases for the `lambda_handler` function (main entry point).

    This uses the S3 stub fixtures and the `send_response` fixture so test cases can
    make assertions against the S3 operations and the response that gets sent back
    to the CloudFormation stack. It also includes the fake lambda `context`.
    """

    def test_delete(self):
        """Test "Delete" Request Type, which is called when the stack is deleted."""
        import helper.website_helper as lambda_function

        # Arrange - Create a "Delete" event.
        event = make_event("Delete")

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # The Delete operation is actually a no-op. We don't delete the S3 objects.
        # The lambda handler just sends a success message back to the CloudFormation stack.
        self.send_response.assert_called_once_with(event, self.context, "SUCCESS", {
            "Message": "Resource deletion successful!"
        })

    def test_copy(self, request_type_copy: str, webapp_manifest: list):
        """Test both "Create" and "Update" request types, which copy files between buckets.

        `request_type_copy` causes this test case to become two test cases:

          * test_copy(Create)
          * test_copy(Update)

        Args:
            request_type_copy (str): "Create" or "Update".
            webapp_manifest (list[str]): List of files contained in the manifest file.
        """
        import helper.website_helper as lambda_function

        # Arrange - Make the Create or Update event.
        event = make_event(request_type_copy)

        # We expect a S3 "copy" request for each entry in the manifest.
        for key in webapp_manifest:
            # Use a helper method to queue up the responses.
            # This will verify each response as it happens.
            self.add_copy_response(event, key)

        # We also expect a "put object" request to update the runtime configuration
        # based on the environment variables defining the configuration.
        self.add_put_object_response(event, "runtimeConfig.json")

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A successful response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "SUCCESS", {
            "Message": "Resource creation successful!"
        })

    def test_copy_no_new_variables(self, webapp_manifest: list, monkeypatch):
        """Test alternate path of copy where we don't update the runtime configuration.

        This is almost the same as `test_copy` except the runtime config doesn't update.
        We don't use `request_type_copy` because we don't need to run it twice.

        Args:
            webapp_manifest (list[str]): List of files contained in the manifest file.
            monkeypatch: This fixture allows us to patch environment variables.
        """
        import helper.website_helper as lambda_function

        # Arrange - Remove one of the required environment variables so the copy
        # function will not find it, and thus, not update the runtime configuration.
        monkeypatch.delenv('UserPoolId')

        # Arrange - Make the Create event. (No need to test again with "Update" also.)
        event = make_event("Create")

        # We expect a S3 "copy" request for each entry in the manifest.
        for key in webapp_manifest:
            # Use a helper method to queue up the responses.
            # This will verify each response as it happens.
            self.add_copy_response(event, key)

        # botocore.stub.Stubber doesn't let us confirm that no request was made.
        # https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html
        # It does, however, let us set expected parameters on a request. So, if we add a
        # fake put object response to the queue, we know any request will trigger a failure.
        # At the end of this test, we make a fake put_object request to clear the queue.
        self.add_put_object_response(event, "should-not-get-any-request")

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A successful response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "SUCCESS", {"Message": "Resource creation successful!"})

        # Now clear the stub's response queue by sending a put object request for the fake object.
        self.eat_put_object_response(lambda_function.s3_client, event, "should-not-get-any-request")

    def test_copy_missing_manifest_file(self):
        """Test that it fails gracefully when the required manifest file doesn't exist.

        This test case is similar to `test_copy` except we don't use the `webapp_manifest`
        fixture to create the required manifest file. Without the manifest file, the
        lambda function doesn't know what files to copy so it must fail.
        """
        import helper.website_helper as lambda_function

        # Arrange - Make the Create event. (No need to test again with "Update" also.)
        event = make_event("Create")

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A failed response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "FAILED", {
            "Message": "Unexpected event received from CloudFormation"
        })

    def test_unsupported_request_type(self):
        """An unsupported request type should send a failed response back."""
        import helper.website_helper as lambda_function

        # Arrange - Make the event with an unsupported request type.
        event = make_event("Unsupported")

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A failed response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "FAILED", {
            "Message": "Unexpected event received from CloudFormation"
        })

    def test_no_request_type(self):
        """Test that an event missing a request type fails gracefully."""
        import helper.website_helper as lambda_function

        # Arrange - Make the event with no event type defined.
        event = make_event("Unsupported")
        del event["RequestType"]

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A failed response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "FAILED", {
            "Message": "Exception during processing: 'RequestType'"
        })

    def test_copy_missing_event_param(self):
        """Test that a malformed event fails gracefully."""
        import helper.website_helper as lambda_function

        # Arrange - Make the Create event but delete a required property.
        event = make_event("Create")
        del event["ResourceProperties"]["WebsiteCodePrefix"]

        # Act - Run the lambda handler
        lambda_function.lambda_handler(event, self.context)

        # Assert - A failed response got sent back to CloudFormation.
        self.send_response.assert_called_once_with(event, self.context, "FAILED", {
            "Message": "Failed to retrieve required values from the CloudFormation event"
        })

    # Helper functions

    def add_copy_response(self, event: dict, key: str):
        """Add responses to the `s3_resource_stub` response queue expecting a copy.

        Args:
            event (dict): The event that will be passed to the lambda handler.
            key (str): The file key from the manifest file.
        """

        # Extract the buckets and source key from the event so we can construct
        # the request arguments.
        source_bucket = event["ResourceProperties"]["WebsiteCodeBucket"]
        source_key = event["ResourceProperties"]["WebsiteCodePrefix"]
        website_bucket = event["ResourceProperties"]["DeploymentBucket"].split('.')[0]

        # Construct the source location arguments.
        copy_source = {
            'Bucket': source_bucket,
            'Key': source_key + '/' + key
        }

        # Construct the full copy arguments including source and destination.
        copy_params = {
            'Bucket': website_bucket,
            'Key': key,
            'CopySource': copy_source
        }

        # Make a fake response for `head_object` with an arbitrary but small content length.
        head_response = {
            'ContentLength': 10
        }

        # `copy` is really a higher level operation that makes multiple requests to S3.
        # The first request is a `head_object` to determine the size of the source file.
        # Since we are giving it a small size (i.e., 10), a simple `copy_object` will do
        # so the following request is the `copy_object`.
        self.s3_resource_stub.add_response('head_object', head_response, expected_params=copy_source)
        self.s3_resource_stub.add_response('copy_object', {}, expected_params=copy_params)

    def add_put_object_response(self, event: dict, key: str):
        """Add a response to the `s3_client_stub` response queue expecting a put object.

        Args:
            event (dict): The event that will be passed to the lambda handler.
            key (str): The file key from the manifest file.
        """

        # Extract the website bucket name from the event so we can construct the arguments.
        website_bucket = event["ResourceProperties"]["DeploymentBucket"].split('.')[0]

        # Set up the expected parameters noting the bucket and key but
        # let any body argument pass.
        put_params = {
            'Bucket': website_bucket,
            'Key': key,
            'Body': ANY
        }

        # Queue up the put object response.
        self.s3_client_stub.add_response('put_object', {}, expected_params=put_params)

    def eat_put_object_response(self, s3_client, event: dict, key: str):
        """Eat a pending put object response by making a request.

        Args:
            s3_client: The actual S3 client instance that we stubbed.
            event (dict): The event that will be passed to the lambda handler.
            key (str): The file key from the manifest file.
        """

        # Extract the website bucket name from the event so we can construct the arguments.
        website_bucket = event["ResourceProperties"]["DeploymentBucket"].split('.')[0]
        # Make the request so it eats up the queued request.
        s3_client.put_object(Bucket=website_bucket, Key=key, Body='')


def make_event(requestType: str) -> dict:
    """Make a fake event in the proper structure with the specified request type."""
    return {
        "RequestType": requestType,
        "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:WebsiteDeployHelper",
        "ResponseURL": "https://localhost/cloudformation-custom-resource-response-uswest2/",
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/WebStack/web-stack-id",
        "RequestId": "11111111-2222-3333-4444-555555555555",
        "LogicalResourceId": "CopyWebSource",
        "ResourceType": "Custom::WebsiteDeployHelper",
        "ResourceProperties": {
            "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:WebsiteDeployHelper",
            "DeploymentBucket": "testWebsiteBucket",
            "WebsiteCodePrefix": "content-localization-on-aws/x.y.z/website",
            "WebsiteCodeBucket": "websiteCodeBucket-us-west-2"
        }
    }
