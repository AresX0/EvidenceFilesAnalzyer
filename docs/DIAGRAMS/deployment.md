```mermaid
graph LR
  subgraph Local
    Dev[Developer Machine]
    Dev -->|venv| App[FileAnalyzer (venv)]
    App --> DB[SQLite DB]
    App --> Reports[Reports folder]
    App --> Playwright[Playwright browsers (optional)]
  end

  subgraph CI
    CI_Runner[CI Runner]
    CI_Runner -->|headless| Tests[pytest (headless)]
    CI_Runner -->|windows| GUI_Tests[pytest (Windows runner with Tk)]
    CI_Runner --> Artifacts[Build artifacts / reports]
  end

  Dev -->|push| GitHub[GitHub Repo]
  GitHub --> CI_Runner
  CI_Runner --> Artifacts --> Dev
```