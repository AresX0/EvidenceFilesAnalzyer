```mermaid
erDiagram
    EVIDENCE_FILE {
        int id PK
        string path
        int size
        datetime mtime
        string sha256
        boolean processed
        json file_metadata
    }

    EXTRACTED_TEXT {
        int id PK
        int file_id FK -> EVIDENCE_FILE.id
        int? page
        text text
        json provenance
    }

    ENTITY {
        int id PK
        int file_id FK -> EVIDENCE_FILE.id
        string entity_type
        string text
        string span
        json provenance
        string confidence
    }

    EVENT {
        int id PK
        text description
        string timestamp
        json provenance
    }

    TRANSCRIPTION {
        int id PK
        int file_id FK -> EVIDENCE_FILE.id
        text text
        json segments
        json provenance
        datetime created_at
    }

    FACE_MATCH {
        int id PK
        string source
        json probe_bbox
        string subject
        string gallery_path
        float distance
        datetime created_at
    }

    EVIDENCE_FILE ||--o{ ENTITY : contains
    EVIDENCE_FILE ||--o{ EXTRACTED_TEXT : has
    EVIDENCE_FILE ||--o{ TRANSCRIPTION : has
    FACE_MATCH }o--|| EVIDENCE_FILE : source
```