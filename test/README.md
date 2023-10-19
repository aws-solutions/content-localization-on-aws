# Media Insights Content Localization Testing - How To

### Overview

Content Localization has the following types of tests:


*Unit:* Tests for each of the Python components found in the `source`
directory of the project.  Scope is the code itself, checks for
introduction of bugs by syntax errors, white-space issues, correct flow
control and order of execution, etc.

Unit tests can be run locally without building nor deploying the stack.

*End to End:* Tests of each functional component of the framework with each other and all dependencies. Scope is the ensure all components work successfully to perform the expected function, e.g. ensure the workflowapi can successfully communicate with the dataplaneapi and successfully complete a workflow

*These tests require Content Localization on AWS to be deployed.*


You can find each of these within the `test` directory of the project


### Unit Tests

These tests are invoked by running the `run_unit.sh` script in the
`test/unit` directory. The script optionally takes positional arguments
for the components to run the tests against. If one or more positional
arguments are supplied, test for each component specified will run. If
no positional argument is supplied, all tests will run:

Examples:

* `./run_unit.sh`
* `./run_unit.sh consumer`
* `./run_unit.sh helper anonymized-data-logger`

Otherwise it runs all available unit tests when no arguments are passed


### End to End tests

Before these tests are run, you must have a healthy Content Localization
on AWS and Media Insights on AWS deployment in your AWS account.

You also need to set the following environment variables:

* `MIE_REGION` - The AWS region your deployment is in
* `MIE_STACK_NAME` - The name of your Media Insights on AWS CloudFormation stack
* `APP_ENDPOINT` - The URL for the Content Localization web application
* `AWS_ACCESS_KEY_ID` - A valid AWS Access Key
* `AWS_SECRET_ACCESS_KEY` - A valid AWS Secret Access Key
* `APP_USERNAME` - A valid username to use to log in to the web application
* `APP_PASSWORD` - web application password for the username

If you are using temporary STS credentials, you also need to set the session token:

* `AWS_SESSION_TOKEN` - For use with STS temporary credentials

*Note, the IAM credentials you specify must belong to an IAM principal that
has administrator permissions on the Media Insights on AWS API's.*

These tests are invoked by running the `run_e2e.sh` script in the `test/e2e` directory.


### Debugging the selenium e2e tests

Here are some debug tips to diagnose failing tests and help with extending them to new features.  The tests are implemented using the [Selenium Chrome webdriver for python](https://selenium-python.readthedocs.io/api.html#module-selenium.webdriver.chrome.webdriver).  Refer to these docs for different capabilities for this utility.

#### Skip workflow setup for tests

There are a number of pytest fixtures that are used to setup the AWS resources and workflow that are required for the e2e tests.  The workflows that are created take 10-15 minutes to setup.  When debugging it can be useful to reuse the workflow from a previous test run.  You need to be careful that the test you are working with won't modify the workflow in non-deterministic ways.  For the existing tests, the workflow is not modified.

To skip workflow creating for individual test, you can use the environment variable before running the test:

* `USE_EXISTING_WORKFLOW` - when this environment variable is set, the pytest fixtures to create a content localization workflow is skipped

#### View the test execution in the browser

The selenium driver is setup to run in headless mode.  You can disable headless mode by commenting out the chrome driver setting in the test case you are running:

```
#chrome_options.add_argument("--headless")
```

### Coverage

#### test\_app.py

This test checks the web app pages created for a workflow. It clicks through the pages, clicks on form elements and fills in inputs.  It doesn't modify the workflow result in any way.

#### test\_reprocess.py

This test checks the reprocessing functions of the web app.  It modifies the subtitles output by the workflow and saves the edits so the workflow will reprocess the downstream assets.
