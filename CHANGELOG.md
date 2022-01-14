# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - tbd

### New:

* Upgrade MIE dependency to v4.0.0
* Document instructions for starting workflows from the command line and from an S3 trigger. (#266)
* Make it easier to find the video workflow in AWS Step Functions by recording the workflow's state machine ARN in the outputs for the VideoWorkflow cloud formation stack (#268)
* Support the new languages and variants recently added to Transcribe and Translate (#263)

### Fixed:

* Fix invalid table format that's used when saving custom vocabularies (#260)
* Fix video load error that occurs with large caption data (#239)
* Make language selection UX for Translate behave more intuitively (#228)
* Fix forever spinner that occurs when there is no data (#225)
* Fix the missing red video player position marker (#224)
* Add missing option to download SRT formatted subtitles
* Fix broken video player for S3 triggered workflows (#271)
* Use the correct source language when saving a new or updated custom vocabulary (#258)


## [1.0.0] - 2021-11-3
### Added
- CHANGELOG version 1.0.0 release
