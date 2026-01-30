# Boomi XML Validation (CI)

This workflow validates Boomi process XML files on pull requests to ensure they meet production safety standards.

## What It Checks
- **Error handling required**
  Each process must include at least one `returndocuments` shape with a label containing **“Error”** (case-insensitive).
- **No deprecated components**
  XMLs must not reference blocklisted `componentId` values.

## When It Runs
- On **pull requests**
- Only when files under `boomi-processes/**/*.xml` change

## Outputs
- **Job Summary** (GitHub Actions → Summary tab)
- **PR comment** with a Markdown report
- **Failing check** if any XML violates rules

## Files
- `.github/workflows/boomi-xml-validation.yml` — GitHub Actions workflow
- `scripts/validate_boomi_xml.py` — XML validation logic
- `scripts/requirements.txt` — Python dependencies

## Exit Codes
- `0` — all files passed
- `1` — one or more files failed
- `2` — invalid usage or fatal error

## Usage (local)
```bash
pip install -r scripts/requirements.txt
python scripts/validate_boomi_xml.py boomi-processes/*.xml
