# Changelog

## Unreleased

### Added
- Add an optional interactive Colab session manager for Conda activation. It detects the configured session, reports CLI-visible compute usage, and offers session/account recovery when the session is unavailable.
- Explain that Google does not publish a fixed free-tier compute quota through the CLI used by aFold21; therefore a reliable quota percentage and 90%-used warning cannot be calculated.

### Safety and limitations
- Account switching triggers the OAuth flow supported by `google-colab-cli` 0.7.x through an authenticated status request; it does not call a nonexistent `colab login` command. Existing tokens are backed up before switching.
- Activation checks run only in interactive terminals; batch and non-interactive shells are not prompted and do not consume stdin.
- Creating a GPU session remains an explicit menu choice. Activating the environment does not silently create a runtime.
- The displayed compute-unit balance is not a measure of free-tier quota remaining.
