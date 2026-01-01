# CI Snippets

## Headless (Ubuntu) - run unit tests quickly
.github/workflows/ci-headless.yml
```yaml
name: CI (headless)
on: [push, pull_request]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -q
``` 

## Windows GUI (Windows runner) - runs GUI-capable tests
.github/workflows/ci-windows-gui.yml
```yaml
name: CI (Windows GUI)
on: [workflow_dispatch]
jobs:
  gui-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Install Playwright browsers
        run: python -m playwright install
      - name: Run GUI tests (gated)
        run: pytest tests -k "not headless_only" -q
``` 

Notes:
- GUI tests should be gated or labeled to avoid running on headless runners.
- Add matrix jobs for multiple Python versions or OSes as needed.
