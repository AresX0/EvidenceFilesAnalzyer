```mermaid
graph TD
  User[Developer/User] --> CLI[CLI / scripts/run_full_scan]
  CLI --> Core[Core Pipeline]
  Core --> Parsers[Parsers & Extractors]
  Parsers --> Sources[(Files / Streams)]
  Core --> Analyzers[Analyzers (face_search / entity)]
  Analyzers --> DB[(SQLite DB)]
  DB --> Reports[Reports (JSON/CSV/HTML)]
  Reports --> GUI[GUI (People Explorer)]
  GUI --> User
  CLI --> Reports
```
