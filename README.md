# vCard Duplicate Merger

Merge, analyze, and export contacts from a `.vcf` (vCard) file with configurable de-duplication strategies.

## ✨ Features
-## ⚡ Quickstart
```bash
# 1. Install dependency
pip install vobject

# 2. Run with GUI dialogs
python merge_vcards.py

# 3. (Headless) Merge to CSV with safe merge & log
python merge_vcards.py -i contacts.vcf -o merged.csv --format csv --safe-merge --log
```
Minimal safest start (avoid over-merging):
```bash
python merge_vcards.py -i contacts.vcf -o merged.vcf --safe-merge --dedupe-key FN,EMAIL
```

Virtual env (Windows PowerShell one-liner):
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install vobject; python merge_vcards.py
```
Unix-like shell:
```bash
python -m venv .venv && source .venv/bin/activate && pip install vobject && python merge_vcards.py
```

- GUI or headless CLI usage.
- Flexible duplicate keys: `FN` only (default) or composite keys like `FN,EMAIL` / `FN,EMAIL,TEL`.
- Safe merge mode: prevents over-merging when only the name matches.
- CSV export with customizable columns (e.g. `FN,EMAIL,TEL,ORG,TITLE`).
- Merge decision logging (`--log`) for audit / review.
- Optional: disable merging (`--no-merge`) to just normalize / export.
- Normalization helpers: lowercasing emails, digit-only comparison for phone numbers when grouping.
- Skips malformed / nameless cards and reports counts.

## 🛠 Requirements
- Python 3.10+
- Dependency: `vobject`

Install:
```bash
pip install vobject
```

## 🚀 Quick Start (GUI Flow)
```bash
python merge_vcards.py
```
1. Pick the input `.vcf` file in the file-open dialog.
2. Choose where to save the merged output (defaults to `yourfile.merged.vcf`).
3. Read the summary printed in the terminal.

## 🧪 Virtual Environment (Recommended)
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install vobject
python merge_vcards.py
```

## 📦 CLI Usage (Headless)
```
python merge_vcards.py -i input.vcf -o merged.vcf
```

### Key Options
| Option | Description |
|--------|-------------|
| `-i / --input` | Input vCard file (skip GUI). |
| `-o / --output` | Output file path (extension auto-adjusted by `--format`). |
| `--dedupe-key` | Comma-separated list of properties to form duplicate key. Default: `FN`. |
| `--safe-merge` | Only merge a group if at least one email OR phone number is shared among its cards. |
| `--no-merge` | Disable merging entirely (just parse + filter + export). |
| `--format` | `vcf` (default) or `csv`. |
| `--csv-fields` | Column list for CSV (default: `FN,EMAIL,TEL,ORG,TITLE`). |
| `--log` | Write a `.merge_log.txt` file beside the output with decisions. |
| `--no-gui` | Fail instead of showing dialogs when paths are missing. |

### Examples
Deduplicate by name only (default):
```bash
python merge_vcards.py -i contacts.vcf -o merged.vcf
```

More conservative merging using name + email:
```bash
python merge_vcards.py -i contacts.vcf -o merged.vcf --dedupe-key FN,EMAIL
```

Use safe merge (guard against people with same name, no shared contact info):
```bash
python merge_vcards.py -i contacts.vcf -o merged.vcf --safe-merge
```

Create a CSV export only (no merging):
```bash
python merge_vcards.py -i contacts.vcf -o contacts.csv --format csv --no-merge
```

CSV with custom columns:
```bash
python merge_vcards.py -i contacts.vcf --format csv --csv-fields FN,EMAIL,TEL,ORG,URL -o out.csv
```

Log merge decisions:
```bash
python merge_vcards.py -i contacts.vcf -o merged.vcf --log
```

All safety + auditing:
```bash
python merge_vcards.py -i contacts.vcf -o merged.csv --format csv --dedupe-key FN,EMAIL,TEL --safe-merge --log
```

## 🔍 How Duplicate Detection Works
1. Cards are parsed; any without a non-empty `FN` or that cannot be parsed increment the "malformed" count.
2. For each card, a composite key is built from the properties listed in `--dedupe-key` (default: `FN`).
	- `EMAIL`: lowercased; duplicates collapsed.
	- `TEL`: digits only used for key comparison (e.g., `+1 (555) 777-9999` → `15557779999`).
	- Other properties: first textual value.
3. Cards sharing the same composite key form a group.

## 🤝 Merge Behavior
- Standard merge: take the first card in the group as the base, copy over unique serialized property lines (excluding `N` and `FN`).
- Safe merge (`--safe-merge`): only merge if any phone OR email value appears in more than one card within the group; otherwise all original cards are kept separately (group becomes multiple records again).
- `--no-merge`: skip merging entirely; each valid card is exported.

## 📄 CSV Export Semantics
- Each column corresponds to a vCard property name (case-insensitive).
- Multivalue properties (`EMAIL`, `TEL`, etc.) are joined with `;` (duplicates removed in order of appearance).
- `N` (structured name) is flattened into a space-joined string of its components if requested.
- Phone numbers in CSV are not forcibly reformatted (beyond merging logic normalization); digits-only version is used only for grouping.

## 🗂 Merge Log (`--log`)
Creates `<output>.merge_log.txt` containing lines like:
```
MERGED key=john smith||john@example.com cards=2 added_fields=3
SKIP (unsafe) group key=jane doe|| size=2 (no shared email/phone)
```
Use this to audit which contacts were merged or skipped.

## 🧩 Choosing a Strategy
| Scenario | Suggested Flags |
|----------|-----------------|
| Contacts exported from a single phone with minor duplicates | (default) |
| Multiple sources combined; risk of same-name different people | `--safe-merge` or `--dedupe-key FN,EMAIL` |
| Aggressive consolidation | `--dedupe-key FN,EMAIL,TEL` |
| Just produce a flat CSV report | `--no-merge --format csv` |
| Forensic: see exactly what merged | `--log --safe-merge` |

## ❓ Troubleshooting / FAQ
**Missing contacts after earlier version?** Enable `--safe-merge` and possibly widen `--dedupe-key` (include `EMAIL`).

**Different people with same name merged together?** Use `--safe-merge` and/or include `EMAIL` or `TEL` in `--dedupe-key`.

**Why are some cards skipped?** They lacked a usable `FN` or failed to parse.

**Phones look inconsistent in CSV.** Add a post-processing step or adapt export logic; grouping already normalizes digits for matching.

**Need JSON output?** Not implemented yet—open an issue or extend `save_csv` with a JSON sibling.

## 🔄 Changelog (Recent)
- Added CLI arguments (`--dedupe-key`, `--safe-merge`, `--no-merge`, `--log`).
- Added CSV export (`--format csv`, `--csv-fields`).
- Added merge decision logging.
- Added safe merge heuristic (shared email/phone requirement).

## 🏗 Possible Future Enhancements
- JSON / SQLite export
- Interactive TUI review of merge groups
- Advanced field normalization (address comparison, fuzzy names)
- Weighted scoring merge decisions

## ⚖ License
MIT (add a standalone `LICENSE` file if distributing publicly).

---
Feel free to adapt / extend—PRs welcome.
