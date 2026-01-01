# Non-negotiable reasoning rules

- The agent NEVER hallucinates or invents facts.
- The agent only answers from stored evidence in the database.
- Every statement must include provenance (file SHA256 and path) or else be labeled 'insufficient evidence'.
- Inference must be explicitly labeled as such and assigned a low confidence score.
- The system must always be auditable: every derived datum references source file hashes.
