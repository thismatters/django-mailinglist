# Changelog
Changes to this project will be documented in this file.

## [Unreleased]
### Added
### Changed
### Removed
### Fixed

## [0.1.6]
### Fixed
- Unsupported operator for MySQL database backend. (#11)

## [0.1.6]
### Added
- Link to manage subscriptions page from the unsubscribe page
### Removed
- Some unnecssary code for dynamically importing modules
### Fixed
- Documentation reference to management command

## [0.1.5]
### Added
- Demo of pluggable user model to `test_project`.
### Fixed
- **BREAKING!** Pluggable user model. This requires that you roll back your migrations for this app and reapply them.
- Project URL in setup.py.

## [0.1.4]
### Added
- Models graph to documentation
- Docs badge to readme

## [0.1.3]
### Added
- `MessageAttachment` model and machinery to manage and send attachments.
- `List-Unsubscribe` header to outgoing messages.
- Lots of documentation!
- Contents to `message_subject.txt` template.
- Management command, celery tasks for processing published submissions.
- View and URL for index of mailing list archives.
- Documentation generation within CI pipeline
### Changed
- More fiddling with the badges
- Message preparation pipeline to reduce template lookups
### Removed
- `Message.subject`

## [0.1.2]
### Changed
- Readme to point to correct github workflow status

## [0.1.1]
### Added
- Nothing, just getting CI pipeline working

## [0.1.0]
### Added
- Everything
