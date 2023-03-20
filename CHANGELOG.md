# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Added ServiceCatalog AppRegistry resources
* Added unit tests for lambda code written in Python

### Fixed

* The "Download Data" button on the **Celebrities** works now.
* Fixed upload of WebVTT files as "Existing Subtitles".

## [2.0.2] - 2023-01-11

### Fixed

* Updated python packages
* Replaced deprecated python command with python3

## [2.0.1] - 2022-08-18

### Fixed

* Version bumped python runtime for web helper lambda function which was preventing successful deployment

## [2.0.0] - 2022-03-01

### Added

* Upgrade MIE dependency to v4.0.1
* Add support for using custom language models with Transcribe (#297)
* Document instructions for starting workflows from the command line and from an S3 trigger. (#266)
* Record the state machine ARN for the VideoWorkflow in cloud formation outputs. This makes it easier to find the video workflow in AWS Step Functions. (#268)
* Support the new languages and variants recently added to Transcribe and Translate (#263)
* Add option to see API requests for computer vision results in the front-end (#303)
* Save filenames to Opensearch so assets can be found by searching for their filename (#249)
* Add an option to auto-detect source language (#209)

### Fixed

* Fix missing data in line chart for computer vision results (#303)
* Fix opensearch throttling (#303)
* Remove unused subtitles checkbox from Upload view (#300)
* Avoid showing empty operator configurations in media summary view (#299)
* Fix miscellaneous bugs in the workflow configuration used to save subtitle edits (#286, #289)
* Fix invalid table format that's used when saving custom vocabularies (#260)
* Fix video load error that occurs with large caption data (#239)
* Support filenames with multiple periods (#237)
* Make language selection for Translate behave more intuitively (#228)
* Fix forever spinner that occurs when there is no data (#225)
* Fix the missing red video player position marker (#224)
* Add missing option to download SRT formatted subtitles (#272)
* Fix broken video player for S3 triggered workflows (#271)
* Fix invalid table format that's used when saving custom vocabularies (#260)
* Use the correct source language when saving a new or updated custom vocabulary (#258)
* Fix bug in WebCaptions that occurs when using source language autodetection in Transcribe (#306)
* Removed profanity checker due to insufficient support for non-english languages (#256)

## [1.0.0] - 2021-11-03

### Added

* CHANGELOG version 1.0.0 release
