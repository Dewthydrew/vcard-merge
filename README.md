# vCard Tools Suite

A comprehensive toolkit for managing vCard files, featuring duplicate merging, corruption recovery, and an advanced vCard viewer/editor.

## 🛠 Tools Included

### 1. merge_vcards.py - Advanced vCard Merger
Merge, analyze, and export contacts from `.vcf` (vCard) files with configurable de-duplication strategies.

### 2. viewer.py - vCard Viewer & Corruption Recovery Tool
A full-featured GUI application for viewing, editing, and recovering corrupted vCard files.

##  Features

### merge_vcards.py
- GUI or headless CLI usage
- Flexible duplicate keys: `FN` only (default) or composite keys like `FN,EMAIL` / `FN,EMAIL,TEL`
- Safe merge mode: prevents over-merging when only the name matches
- CSV export with customizable columns (e.g. `FN,EMAIL,TEL,ORG,TITLE`)
- Merge decision logging (`--log`) for audit / review
- Optional: disable merging (`--no-merge`) to just normalize / export
- Normalization helpers: lowercasing emails, digit-only comparison for phone numbers when grouping
- Skips malformed / nameless cards and reports counts

### viewer.py
- **Corruption Recovery**: Load and repair severely corrupted vCard files (Outlook exports, etc.)
- **Advanced Viewing**: Browse contacts with keyboard navigation (arrow keys, Page Up/Down)
- **Real-time Editing**: Edit raw vCard data with syntax highlighting
- **Contact Management**: Add/delete contacts, alphabetical sorting
- **Resizable Interface**: Adjustable sidebar, responsive layout
- **Clean Export**: Export corruption-free vCard files with detailed recovery statistics
- **Corruption Analysis**: Detailed reports on corruption patterns found in files
- **Multi-format Support**: Handle various vCard versions and formats

##  Quick Start

### Install Dependencies
```bash
pip install vobject
```

### Merge vCards (GUI)
```bash
python merge_vcards.py
```

### View/Repair vCards (GUI)
```bash
python viewer.py
```

### Command Line Merging
```bash
# Safe merge with logging
python merge_vcards.py -i contacts.vcf -o merged.csv --format csv --safe-merge --log

# Conservative merge (avoid over-merging)
python merge_vcards.py -i contacts.vcf -o merged.vcf --safe-merge --dedupe-key FN,EMAIL
```

### Virtual Environment Setup
**Windows PowerShell:**
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install vobject
```

**Unix-like shell:**
```bash
python -m venv .venv && source .venv/bin/activate && pip install vobject
```

## 🛠 Requirements
- Python 3.10+
- Dependency: `vobject`

Install:
```bash
pip install vobject
```

## � Detailed Usage

### merge_vcards.py - vCard Merger

#### GUI Mode
```bash
python merge_vcards.py
```
1. Pick the input `.vcf` file in the file-open dialog
2. Choose where to save the merged output (defaults to `yourfile.merged.vcf`)
3. Read the summary printed in the terminal

#### CLI Mode (Headless)
```
python merge_vcards.py -i input.vcf -o merged.vcf
```

#### Key Options
| Option | Description |
|--------|-------------|
| `-i / --input` | Input vCard file (skip GUI) |
| `-o / --output` | Output file path (extension auto-adjusted by `--format`) |
| `--dedupe-key` | Comma-separated list of properties to form duplicate key. Default: `FN` |
| `--safe-merge` | Only merge a group if at least one email OR phone number is shared among its cards |
| `--no-merge` | Disable merging entirely (just parse + filter + export) |
| `--format` | `vcf` (default) or `csv` |
| `--csv-fields` | Column list for CSV (default: `FN,EMAIL,TEL,ORG,TITLE`) |
| `--log` | Write a `.merge_log.txt` file beside the output with decisions |
| `--no-gui` | Fail instead of showing dialogs when paths are missing |

#### Examples
```bash
# Deduplicate by name only (default)
python merge_vcards.py -i contacts.vcf -o merged.vcf

# Conservative merging using name + email
python merge_vcards.py -i contacts.vcf -o merged.vcf --dedupe-key FN,EMAIL

# Safe merge (guard against people with same name, no shared contact info)
python merge_vcards.py -i contacts.vcf -o merged.vcf --safe-merge

# Create a CSV export only (no merging)
python merge_vcards.py -i contacts.vcf -o contacts.csv --format csv --no-merge

# CSV with custom columns
python merge_vcards.py -i contacts.vcf --format csv --csv-fields FN,EMAIL,TEL,ORG,URL -o out.csv

# All safety + auditing
python merge_vcards.py -i contacts.vcf -o merged.csv --format csv --dedupe-key FN,EMAIL,TEL --safe-merge --log
```

### viewer.py - vCard Viewer & Corruption Recovery

#### Launch the Viewer
```bash
python viewer.py
```

#### Key Features & Controls
- **File → Open vCard File**: Load any `.vcf` file, including corrupted ones
- **File → Export Clean vCards**: Export corruption-free vCards with recovery statistics
- **Arrow Keys**: Navigate through contacts
- **Page Up/Down**: Fast navigation
- **Edit Panel**: Modify raw vCard data in real-time
- **Add Contact**: Create new vCard entries
- **Delete Contact**: Remove selected contacts
- **Sort**: Alphabetical sorting by name, email, or phone
- **Resizable Sidebar**: Drag the edge to adjust layout

#### Corruption Recovery
The viewer can recover contacts from severely corrupted files:
- **Outlook Export Corruption**: Removes "This contact is read-only" messages
- **UI Fragment Cleanup**: Eliminates "tap the li" and other interface text
- **Encoding Issues**: Fixes excessive backslashes and malformed characters
- **Base64 Garbage**: Removes corrupted binary data
- **Recovery Statistics**: Detailed reports on what was recovered vs. skipped

#### Export Options
When exporting cleaned vCards, the tool provides:
- **Multi-layer Recovery**: Multiple fallback methods to save contacts
- **Progress Reporting**: Real-time feedback on recovery success
- **Quality Validation**: Ensures exported contacts have meaningful data
- **Recovery Rate**: Percentage of successfully recovered contacts

## 🔍 Technical Details

### How Duplicate Detection Works (merge_vcards.py)
1. Cards are parsed; any without a non-empty `FN` or that cannot be parsed increment the "malformed" count
2. For each card, a composite key is built from the properties listed in `--dedupe-key` (default: `FN`)
   - `EMAIL`: lowercased; duplicates collapsed
   - `TEL`: digits only used for key comparison (e.g., `+1 (555) 777-9999` → `15557779999`)
   - Other properties: first textual value
3. Cards sharing the same composite key form a group

### Merge Behavior
- **Standard merge**: take the first card in the group as the base, copy over unique serialized property lines (excluding `N` and `FN`)
- **Safe merge** (`--safe-merge`): only merge if any phone OR email value appears in more than one card within the group; otherwise all original cards are kept separately
- **No merge** (`--no-merge`): skip merging entirely; each valid card is exported

### CSV Export Semantics
- Each column corresponds to a vCard property name (case-insensitive)
- Multivalue properties (`EMAIL`, `TEL`, etc.) are joined with `;` (duplicates removed in order of appearance)
- `N` (structured name) is flattened into a space-joined string of its components if requested
- Phone numbers in CSV are not forcibly reformatted (beyond merging logic normalization); digits-only version is used only for grouping

### Corruption Recovery (viewer.py)
The viewer uses advanced parsing techniques to recover corrupted vCard data:

#### Recovery Methods
1. **Ultra-permissive parsing**: Splits files manually instead of relying on strict vCard parsers
2. **Pattern-based cleaning**: Removes known corruption patterns (Outlook messages, UI fragments, etc.)
3. **Multi-layer export**: Uses multiple fallback methods when standard serialization fails
4. **Manual reconstruction**: Rebuilds vCards from individual properties when automatic methods fail
5. **Rescue mode**: Creates minimal vCards as last resort to preserve at least contact names

#### Common Corruption Patterns Handled
- **Outlook interface contamination**: "This contact is read-only" messages
- **UI fragment pollution**: "tap the li" and similar interface text
- **Encoding corruption**: Excessive backslashes and escape sequences
- **Base64 garbage**: Corrupted binary data mixed with contact information
- **Structural damage**: Missing END:VCARD tags, malformed property lines

### Merge Log Format (`--log`)
Creates `<output>.merge_log.txt` containing lines like:
```
MERGED key=john smith||john@example.com cards=2 added_fields=3
SKIP (unsafe) group key=jane doe|| size=2 (no shared email/phone)
```
Use this to audit which contacts were merged or skipped.

##  Choosing a Strategy

### For merge_vcards.py
| Scenario | Suggested Flags |
|----------|-----------------|
| Contacts exported from a single phone with minor duplicates | (default) |
| Multiple sources combined; risk of same-name different people | `--safe-merge` or `--dedupe-key FN,EMAIL` |
| Aggressive consolidation | `--dedupe-key FN,EMAIL,TEL` |
| Just produce a flat CSV report | `--no-merge --format csv` |
| Forensic: see exactly what merged | `--log --safe-merge` |

### For viewer.py
| Use Case | Workflow |
|----------|----------|
| **Corrupted vCard files** | Open file → View corruption analysis → Export clean vCards |
| **Contact browsing** | Open file → Use arrow keys to navigate → View/edit in right panel |
| **Bulk editing** | Open file → Select contacts → Edit raw vCard data → Save |
| **Format conversion** | Open file → File → Export Clean vCards (removes corruption) |
| **Data recovery** | Open severely corrupted file → Review recovery statistics → Export rescued contacts |

##  Use Cases & Examples

### Scenario 1: Outlook Export Recovery
Your Outlook exported a corrupted vCard file:
```bash
# Use the viewer to recover and clean
python viewer.py
# File → Open → select corrupted file
# File → Export Clean vCards → review recovery stats
```

### Scenario 2: Merge Multiple Contact Sources
You have contacts from phone, email, and social media:
```bash
# Conservative merge to avoid combining different people with same name
python merge_vcards.py -i all_contacts.vcf -o merged.vcf --safe-merge --dedupe-key FN,EMAIL --log
```

### Scenario 3: Create Contact Database
Convert vCards to searchable CSV:
```bash
# Export all fields to CSV without merging
python merge_vcards.py -i contacts.vcf -o database.csv --format csv --no-merge --csv-fields FN,N,EMAIL,TEL,ORG,TITLE,ADR,URL
```

### Scenario 4: Audit Duplicate Merging
Review exactly what gets merged:
```bash
# Generate detailed merge log
python merge_vcards.py -i contacts.vcf -o cleaned.vcf --safe-merge --log
# Review the .merge_log.txt file
```

## Troubleshooting / FAQ

### merge_vcards.py Issues
**Q: Missing contacts after merging?**  
A: Enable `--safe-merge` and possibly widen `--dedupe-key` (include `EMAIL`)

**Q: Different people with same name merged together?**  
A: Use `--safe-merge` and/or include `EMAIL` or `TEL` in `--dedupe-key`

**Q: Why are some cards skipped?**  
A: They lacked a usable `FN` or failed to parse

**Q: Phone numbers look inconsistent in CSV**  
A: Add a post-processing step or adapt export logic; grouping already normalizes digits for matching

### viewer.py Issues
**Q: Viewer shows "X entries skipped" - is this bad?**  
A: Not necessarily. Skipped entries are often empty vCard shells or severely corrupted data with no recoverable information

**Q: Can't load a vCard file?**  
A: The viewer uses ultra-permissive parsing. If it can't load, the file may have fundamental encoding issues. Try opening in a text editor first

**Q: Exported file is smaller than original?**  
A: This is normal for corrupted files. The export removes corruption and empty entries, keeping only valid contact data

**Q: How do I know if corruption recovery worked?**  
A: The export dialog shows detailed statistics: "X contacts successfully exported, Y contacts could not be recovered, Recovery rate: Z%"

## Recent Enhancements

### merge_vcards.py
- Added CLI arguments (`--dedupe-key`, `--safe-merge`, `--no-merge`, `--log`)
- Added CSV export (`--format csv`, `--csv-fields`)
- Added merge decision logging
- Added safe merge heuristic (shared email/phone requirement)

### viewer.py (New)
- Full-featured vCard viewer with corruption recovery
- Real-time editing capabilities
- Keyboard navigation and resizable interface
- Advanced corruption analysis and pattern detection
- Multi-layer export with recovery statistics
- Support for severely damaged vCard files

## Future Enhancements
- JSON / SQLite export
- Interactive TUI review of merge groups  
- Advanced field normalization (address comparison, fuzzy names)
- Weighted scoring merge decisions
- Integration between merger and viewer tools
- Batch processing capabilities

## License
MIT (add a standalone `LICENSE` file if distributing publicly)

---
**Need help?** Open an issue or check the troubleshooting section above.  
**Want to contribute?** PRs welcome for both tools!
