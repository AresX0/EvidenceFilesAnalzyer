# Testing Guide

## Running tests
- Run the full suite:
  - pytest -q
- To run a specific test file or test:
  - pytest tests/test_some_file.py::test_name -q

## GUI tests
- Some GUI tests require Tk/Tcl and image support and will be skipped automatically when the environment is headless or PhotoImage is unavailable.
- Use `case_agent.utils.tk_helper.is_tk_usable()` (or equivalent) in tests to gate GUI-specific assertions.

## Adding tests
- Prefer headless unit tests by extracting logic into testable models (e.g., `VirtualThumbGridModel`).
- Mock heavy IO (requests, Playwright, file downloads) in unit tests.
- For GUI behavior, prefer small integration tests that assert non-blocking initialization and graceful error-handling.

## CI Recommendations
- Add a matrix with at least two jobs: headless (fast) and GUI-enabled (Windows runner with Tk).
- Ensure tests that require Playwright or external browsers are gated behind an install step or a separate job.
