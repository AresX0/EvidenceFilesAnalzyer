# Security Notes

## Untrusted Inputs
- Treat file contents as untrusted. Avoid executing or importing code from scanned files.
- Use safe parsers (prefer library-level secure defaults) and sandbox/limit resource usage for heavy parsing tasks.

## Dependencies
- Keep third-party deps up to date; use `pip list --outdated` and pin requirements where necessary.
- Prefer reproducible installs (requirements.freeze.txt or lock file).

## Secrets & Credentials
- Do not commit credentials (e.g., Google Drive service accounts). Use environment variables or `credentials.json` loaded at runtime when required.

## Data handling & Privacy
- Reports can contain sensitive info (face matches, extracted text). Ensure appropriate access controls when sharing.
