import vobject
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog
import os

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
def select_output_file(default_name="merged_contacts.vcf"):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        title="Save merged vCard as...",
        initialfile=default_name,
        defaultextension=".vcf",
        filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
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
def find_duplicates(vcards):
    contacts = defaultdict(list)
    for card in vcards:
        fn = getattr(card, 'fn', None)
        if fn:
            key = fn.value.strip().lower()
            contacts[key].append(card)
    return contacts

# Merge duplicate vCards: combine all unique fields, but only one N and FN field
def merge_contacts(contacts):
    merged = []
    merged_count = 0
    for group in contacts.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            base = group[0]
            seen_lines = set()
            # Always keep only one N and FN field (from base)
            for card in group[1:]:
                for line in card.getChildren():
                    # Skip N and FN fields to avoid duplicates
                    if line.name in ("N", "FN"):
                        continue
                    line_str = line.serialize()
                    if line_str not in seen_lines:
                        seen_lines.add(line_str)
                        if line not in base.getChildren():
                            base.add(line)
            merged.append(base)
            merged_count += len(group) - 1
    return merged, merged_count

# Save merged vCards to a file
def save_vcards(vcards, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for card in vcards:
            f.write(card.serialize())

if __name__ == "__main__":
    input_file = select_vcard_file()
    if not input_file:
        print("No file selected. Exiting.")
        exit(1)
    output_file = select_output_file()
    if not output_file:
        print("No output file selected. Exiting.")
        exit(1)
    print(f"Loading vCards from {input_file}...")
    vcards, malformed = load_vcards(input_file)
    print(f"Loaded {len(vcards)} valid vCards. Skipped {malformed} malformed or missing-name cards.")
    contacts = find_duplicates(vcards)
    merged, merged_count = merge_contacts(contacts)
    save_vcards(merged, output_file)
    print(f"Merged vCards saved to {output_file}")
    print(f"Original contacts: {len(vcards)}")
    print(f"Unique contacts after merge: {len(merged)}")
    print(f"Duplicates merged: {merged_count}")