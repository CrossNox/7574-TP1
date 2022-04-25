# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.10] - 2022-04-25
### Added
- Several docstrings

## [0.9.9] - 2022-04-25
### Fixed
- Error on notification responses converting from bytes
- Use typer to print instead of printing on client CLI

## [0.9.8] - 2022-04-25
### Fixed
- Responsibility of printing is on the CLI, not the Client

## [0.9.7] - 2022-04-25
### Added
- Drop connections if dispatcher is busy
- Drop connections if intention workers are too busy

## [0.9.6] - 2022-04-25
### Added
- Drop metrics when queues are full, reply server unavailable

## [0.9.5] - 2022-04-25
### Added
- Warn about badly formatted metrics
- Warn about badly formatted queries

## [0.9.4] - 2022-04-24
### Added
- Warn about non-existing metric when querying

## [0.9.3] - 2022-04-24
### Fixed
- Pandas indexing to discard metrics

## [0.9.2] - 2022-04-24
### Fixed
- Allow user to control pretty-printing
- Allow user to control logging level

## [0.9.1] - 2022-04-24
### Fixed
- Imports broken on previous version

## [0.9.0] - 2022-04-23
### Added
- Allowed client to use configuration from environment vars

## [0.8.1] - 2022-04-23
### Changed
- Package structure

## [0.8.0] - 2022-04-23
### Added
- Client interface to monitor notifications

## [0.7.1] - 2022-04-23
### Changed
- Server interface
- Server CLI interface
- Server defaults

## [0.7.0] - 2022-04-23
### Added
- Monitoring notifications written to file

## [0.6.0] - 2022-04-22
### Added
- Server defaults from configuration file

## [0.5.0] - 2022-04-22
### Added
- Implemented queries

## [0.4.1] - 2022-04-21
### Fixed
- Missing parameters to the server command

### Changed
- Moved common constants to module

## [0.4.0] - 2022-04-21
### Added
- Writing to partitioned files

## [0.3.0] - 2022-04-19
### Added
- Added command to client to ramp metrics

## [0.2.0] - 2022-04-18
### Added
- Echo server with binary protocol
- Client to send metrics

## [0.1.0] - 2022-04-17
### Added
- Initial commit with basic structure
