import vobject
from collections import defaultdict, Counter
import tkinter as tk
from tkinter import filedialog
import os
import argparse
from typing import List, Dict
import csv
import sys

# Prompt user to select a file
def select_vcard_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select vCard file",
        filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
    )
    return file_path

# Prompt user to select output file name and location
def select_output_file(default_name="merged_contacts.vcf", fmt: str = 'vcf'):
    root = tk.Tk()
    root.withdraw()
    if fmt.lower() == 'csv':
        filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        def_ext = ".csv"
        title = "Save merged contacts as CSV..."
    else:
        filetypes = [("vCard files", "*.vcf"), ("All files", "*.*")]
        def_ext = ".vcf"
        title = "Save merged vCard as..."
    file_path = filedialog.asksaveasfilename(
        title=title,
        initialfile=default_name,
        defaultextension=def_ext,
        filetypes=filetypes
    )
    return file_path

# Load vCards from a file, skip malformed cards
def load_vcards(filename):
    import vobject
    from vobject.base import ParseError
    vcards = []
    malformed = 0
    with open(filename, 'r', encoding='utf-8') as f:
        data = f.read()
    try:
        for v in vobject.readComponents(data):
            try:
                fn = getattr(v, 'fn', None)
                if fn and fn.value.strip():
                    vcards.append(v)
                else:
                    malformed += 1
            except Exception:
                malformed += 1
    except ParseError as e:
        print(f"Parse error: {e}. Some vCards may be malformed and will be skipped.")
        malformed += 1
    return vcards, malformed

# Find duplicates by full name (FN), case-insensitive
def find_duplicates(vcards, key_fields: List[str]):
    """Group cards by a composite key of the requested fields.

    key_fields: list of property names (case-insensitive) e.g. ['FN'] or ['FN','EMAIL'].
    For multivalued fields (EMAIL, TEL) we use a sorted joined list of normalized values.
    Missing fields become empty strings; key is lowercased for stability.
    """
    norm_fields = [f.upper() for f in key_fields if f.strip()]
    if not norm_fields:
        print("Warning: No valid dedupe key fields provided; using FN.")
        norm_fields = ['FN']
    contacts: Dict[str, List] = defaultdict(list)

    for card in vcards:
        key_parts = []
        for field in norm_fields:
            if field == 'FN':
                fn = getattr(card, 'fn', None)
                key_parts.append(fn.value.strip() if fn else '')
            elif field in ('EMAIL', 'TEL'):
                values = []
                for child in card.getChildren():
                    if child.name == field:
                        val = getattr(child, 'value', '')
                        if isinstance(val, str):
                            val_norm = val.strip().lower()
                            if field == 'TEL':
                                digits = ''.join(ch for ch in val_norm if ch.isdigit())
                                if digits:
                                    val_norm = digits
                            values.append(val_norm)
                if values:
                    values = sorted(set(values))
                key_parts.append('|'.join(values))
            else:
                values = []
                for child in card.getChildren():
                    if child.name == field:
                        val = getattr(child, 'value', '')
                        if isinstance(val, str):
                            values.append(val.strip())
                key_parts.append(values[0] if values else '')
        composite = '||'.join(key_parts).lower()
        contacts[composite].append(card)
    return contacts

# Merge duplicate vCards: combine all unique fields, but only one N and FN field
def merge_contacts(contacts, safe_merge: bool = False, merge_log: List[str] = None):
    """Merge grouped contacts.

    safe_merge: if True, only merge a duplicate group when there is strong evidence
    they represent the same person (shared normalized email or phone). Otherwise
    the group is left unmerged (all cards kept).
    merge_log: optional list to append human-readable merge decisions.
    """
    merged = []
    merged_count = 0

    for key, group in contacts.items():
        # Single card -> nothing to merge
        if len(group) == 1:
            merged.append(group[0])
            continue

        def extract_norm(card):
            emails = []
            phones = []
            for line in card.getChildren():
                if line.name == 'EMAIL':
                    val = getattr(line, 'value', '')
                    if isinstance(val, str):
                        emails.append(val.strip().lower())
                elif line.name == 'TEL':
                    val = getattr(line, 'value', '')
                    if isinstance(val, str):
                        digits = ''.join(ch for ch in val if ch.isdigit())
                        if digits:
                            phones.append(digits)
            return set(emails), set(phones)

        cards_norm = [extract_norm(c) for c in group]
        email_counter = Counter()
        phone_counter = Counter()
        for emails, phones in cards_norm:
            email_counter.update(emails)
            phone_counter.update(phones)
        has_shared_email = any(cnt > 1 for cnt in email_counter.values())
        has_shared_phone = any(cnt > 1 for cnt in phone_counter.values())

        if safe_merge and not (has_shared_email or has_shared_phone):
            merged.extend(group)
            if merge_log is not None:
                merge_log.append(
                    f"SKIP (unsafe) group key={key} size={len(group)} (no shared email/phone)"
                )
            continue

        base = group[0]
        seen_lines = {
            child.serialize() for child in base.getChildren()
            if child.name not in ("N", "FN")
        }
        added_lines = 0

        for card in group[1:]:
            for line in card.getChildren():
                if line.name in ("N", "FN"):
                    continue
                line_str = line.serialize()
                if line_str in seen_lines:
                    continue
                seen_lines.add(line_str)
                base.add(line)
                added_lines += 1

        merged.append(base)
        merged_count += len(group) - 1
        if merge_log is not None:
            merge_log.append(
                f"MERGED key={key} cards={len(group)} added_fields={added_lines}"
            )

    return merged, merged_count

def write_merge_log(log_lines: List[str], output_file: str):
    if not log_lines:
        return
    log_path = output_file + '.merge_log.txt'
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        print(f"Merge log written to {log_path}")
    except Exception as e:
        print(f"Failed to write merge log: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description="Merge duplicate vCards with configurable strategies.")
    parser.add_argument('-i', '--input', help='Input .vcf file (skip GUI if provided)')
    parser.add_argument('-o', '--output', help='Output file (extension inferred if --format given)')
    parser.add_argument('--dedupe-key', default='FN', help='Comma-separated list of fields to form duplicate key (default: FN). Example: FN,EMAIL')
    parser.add_argument('--safe-merge', action='store_true', help='Only merge duplicates when they share an email or phone number.')
    parser.add_argument('--no-merge', action='store_true', help='Disable merging (just re-save filtered valid cards).')
    parser.add_argument('--log', action='store_true', help='Write a merge decision log alongside output file.')
    parser.add_argument('--no-gui', action='store_true', help='Fail instead of prompting with GUI dialogs if input/output missing.')
    parser.add_argument('--format', choices=['vcf','csv'], default='vcf', help='Output format: vcf (default) or csv.')
    parser.add_argument('--csv-fields', default='FN,EMAIL,TEL,ORG,TITLE', help='Comma-separated fields for CSV columns (default: FN,EMAIL,TEL,ORG,TITLE). Repeated multivalue fields joined by ;')
    parser.add_argument('--interactive', action='store_true', help='Force interactive prompts for merge parameters.')
    parser.add_argument('--no-interactive', action='store_true', help='Disable interactive prompts even if no parameters supplied.')
    parser.add_argument('--console', action='store_true', help='Force console path prompts instead of GUI file dialogs.')
    return parser.parse_args()

def _prompt(prompt: str, default: str = None, validator=None):
    while True:
        if default is not None:
            raw = input(f"{prompt} [{default}]: ").strip()
            if not raw:
                raw = default
        else:
            raw = input(f"{prompt}: ").strip()
        if validator:
            ok, msg, val = validator(raw)
            if ok:
                return val
            print(f"  ! {msg}")
        else:
            return raw

def interactive_config(args):
    """Interactively ask the user for merge parameters (friendly wizard).

    Also lets the user enter input/output paths directly to avoid hidden GUI dialogs.
    """
    print("\n=== vCard Merge Configuration Wizard ===")
    print("Press Enter to accept the [default] shown in brackets.")

    # Input / output paths (optional here; blank = use dialogs later unless --console)
    if not args.input:
        in_path = _prompt('Input .vcf file path (leave blank to use file dialog)', '')
        if in_path:
            args.input = in_path.strip('"')
    if not args.output:
        out_path = _prompt('Output file path (leave blank to choose in dialog)', '')
        if out_path:
            args.output = out_path.strip('"')

    # Output format
    def fmt_validator(v):
        v2 = v.lower()
        if v2 in ('vcf','csv'):
            return True, '', v2
        return False, 'Format must be vcf or csv', None
    chosen_format = _prompt('Output format (vcf/csv)', args.format, fmt_validator)

    # Dedupe key
    dedupe_key = _prompt('Duplicate key fields (comma separated)', args.dedupe_key)
    # Safe merge
    def yn_validator(v):
        v2 = v.lower()
        if v2 in ('y','yes','n','no'):
            return True, '', v2.startswith('y')
        return False, 'Enter y or n', None
    safe_default = 'y' if args.safe_merge else 'n'
    safe_merge = _prompt('Enable safe merge (require shared email or phone to merge)', safe_default, yn_validator)

    # Disable merge entirely?
    no_merge_default = 'y' if args.no_merge else 'n'
    no_merge = _prompt('Disable merging (keep all duplicates separate)', no_merge_default, yn_validator)

    # Merge log
    log_default = 'y' if args.log else 'n'
    log_enabled = _prompt('Write merge decision log', log_default, yn_validator)

    csv_fields = args.csv_fields
    if chosen_format == 'csv':
        csv_fields = _prompt('CSV columns (comma separated)', args.csv_fields)

    # Apply
    args.format = chosen_format
    args.dedupe_key = dedupe_key
    args.safe_merge = bool(safe_merge) and not no_merge  # safe merge irrelevant if no_merge
    args.no_merge = bool(no_merge)
    args.log = bool(log_enabled)
    args.csv_fields = csv_fields

    print(("\nConfiguration summary:\n"
           f"  Format: {args.format}\n"
           f"  Dedupe key: {args.dedupe_key}\n"
           f"  Safe merge: {args.safe_merge}\n"
           f"  Merging disabled: {args.no_merge}\n"
           f"  Log decisions: {args.log}\n"
           f"  CSV fields: {args.csv_fields if args.format=='csv' else '(n/a)'}"))
    print(f"  Input path: {args.input or '(dialog)'}")
    print(f"  Output path: {args.output or '(dialog)'}")
    print("==========================================\n")
    return args

# Save merged vCards to a file
def save_vcards(vcards, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for card in vcards:
            f.write(card.serialize())

def extract_property_values(card, prop_name: str) -> List[str]:
    prop_name = prop_name.upper()
    values = []
    for child in card.getChildren():
        if child.name == prop_name:
            val = getattr(child, 'value', '')
            if isinstance(val, str):
                values.append(val.strip())
            else:
                try:
                    values.append(str(val))
                except Exception:
                    pass
    return values

def card_to_csv_row(card, field_order: List[str]) -> List[str]:
    row = []
    fn_val = getattr(card, 'fn', None)
    for field in field_order:
        f_upper = field.upper()
        if f_upper == 'FN':
            row.append(fn_val.value.strip() if fn_val else '')
        elif f_upper == 'N':
            # Structured name; join components with space
            n_obj = getattr(card, 'n', None)
            if n_obj and hasattr(n_obj, 'value'):
                try:
                    parts = [p for p in n_obj.value if p]
                    row.append(' '.join(parts))
                except Exception:
                    row.append(str(n_obj.value))
            else:
                row.append('')
        else:
            vals = extract_property_values(card, f_upper)
            if f_upper == 'TEL':
                # Normalize phone digits for consistency but keep original display if needed
                normed = []
                for v in vals:
                    digits = ''.join(ch for ch in v if ch.isdigit())
                    normed.append(digits or v)
                vals = normed
            row.append(';'.join(dict.fromkeys(vals)))  # preserve order remove dup
    return row

def save_csv(vcards, filename, fields: List[str]):
    # Ensure extension
    if not filename.lower().endswith('.csv'):
        filename += '.csv'
    fields_clean = [f.strip() for f in fields if f.strip()]
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(fields_clean)
        for card in vcards:
            writer.writerow(card_to_csv_row(card, fields_clean))
    print(f"CSV saved to {filename}")

if __name__ == "__main__":
    args = parse_args()

    # Determine if interactive wizard should run
    no_user_params = len(sys.argv) == 1  # only script name
    if (no_user_params and not getattr(args, 'no_interactive', False)) or args.interactive:
        # Provide defaults for wizard reflecting current args
        try:
            args = interactive_config(args)
        except EOFError:
            print("Input stream closed; continuing with defaults.")

    # Determine input / output via CLI or GUI
    input_file = args.input
    if not input_file:
        if args.no_gui or args.console:
            print("Input file not provided and GUI disabled (--no-gui). Exiting.")
            exit(1)
        input_file = select_vcard_file()
    if not input_file:
        print("No input file selected. Exiting.")
        exit(1)

    output_file = args.output
    if not output_file:
        if args.no_gui or args.console:
            print("Output file not provided and GUI disabled (--no-gui). Exiting.")
            exit(1)
        # Suggest default name based on input
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        if args.format == 'csv':
            output_file = select_output_file(default_name=f"{base_name}.merged.csv", fmt='csv')
        else:
            output_file = select_output_file(default_name=f"{base_name}.merged.vcf", fmt='vcf')
    if not output_file:
        print("No output file selected. Exiting.")
        exit(1)

    # If user provided an output without extension, add based on format
    if '.' not in os.path.basename(output_file):
        output_file = output_file + ('.csv' if args.format == 'csv' else '.vcf')
    # If mismatch extension vs format, adjust
    if args.format == 'csv' and not output_file.lower().endswith('.csv'):
        output_file = os.path.splitext(output_file)[0] + '.csv'
    if args.format == 'vcf' and not output_file.lower().endswith('.vcf'):
        output_file = os.path.splitext(output_file)[0] + '.vcf'

    print(f"Loading vCards from {input_file}...")
    vcards, malformed = load_vcards(input_file)
    print(f"Loaded {len(vcards)} valid vCards. Skipped {malformed} malformed or missing-name cards.")

    key_fields = [p.strip() for p in args.dedupe_key.split(',') if p.strip()]
    contacts = find_duplicates(vcards, key_fields)

    merge_log: List[str] = [] if args.log else None
    if args.no_merge:
        merged = vcards
        merged_count = 0
        if merge_log is not None:
            merge_log.append("Merging disabled (--no-merge)")
    else:
        merged, merged_count = merge_contacts(contacts, safe_merge=args.safe_merge, merge_log=merge_log)

    if args.format == 'csv':
        csv_fields = [f.strip() for f in args.csv_fields.split(',')]
        save_csv(merged, output_file, csv_fields)
    else:
        save_vcards(merged, output_file)
        print(f"Output saved to {output_file}")
    print(f"Original contacts: {len(vcards)}")
    print(f"Unique contacts after merge: {len(merged)}")
    print(f"Duplicates merged: {merged_count}")
    if args.safe_merge:
        print("Safe merge mode: groups without shared email/phone kept separate.")
    if merge_log is not None:
        write_merge_log(merge_log, output_file)