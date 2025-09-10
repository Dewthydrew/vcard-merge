# vCard Duplicate Merger

A simple Python script to merge duplicate contacts in a `.vcf` (vCard) file. It:
- Loads all contacts from a selected vCard file (GUI file picker)
- Detects duplicates by full name (FN)
- Merges unique fields (skips duplicate N/FN to stay standards-compliant)
- Skips malformed entries and reports counts
- Lets you choose the output filename & location

## Requirements
- Python 3.10+
- `vobject` library (`pip install vobject`)

## Quick Start
```bash
python merge_vcards.py
```
Then:
1. Choose the source `.vcf` file in the dialog.
2. Choose where to save the merged `.vcf`.
3. Check the terminal output for a summary.

## Virtual Environment (Optional)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install vobject
python merge_vcards.py
```

## Notes
- Only one `N` and `FN` field is retained per vCard to avoid validation errors.
- Output file will contain merged, deduplicated contacts.

## Future Ideas
- Add email/phone-based duplicate detection
- CLI flags for headless operation
- Export a CSV report of merged sets

## License
MIT (add a LICENSE file if you need one)
