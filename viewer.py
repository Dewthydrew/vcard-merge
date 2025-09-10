#!/usr/bin/env python3
"""
Simple vCard Viewer - Browse and edit vCard contacts with a GUI interface
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import vobject
import os
import copy


class VCardViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("vCard Viewer")
        self.root.geometry("800x600")
        
        self.vcards = []
        self.filtered_vcards = []  # For search functionality
        self.current_index = 0
        self.is_modified = False  # Track if any changes have been made
        self.current_file = None  # Track current file for saving
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # File selection frame (spans full width)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Select vCard File", command=self.select_file).grid(row=0, column=0, padx=(0, 10))
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # File action buttons
        ttk.Button(file_frame, text="Save As...", command=self.save_as_file).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(file_frame, text="🧹 Export Clean", command=self.export_clean_vcards).grid(row=0, column=3, padx=(5, 0))
        
        # Create resizable paned window
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left sidebar - Contact list
        sidebar_frame = ttk.LabelFrame(self.paned_window, text="Contacts", padding="5")
        self.paned_window.add(sidebar_frame, weight=1)  # Initial weight 1
        sidebar_frame.columnconfigure(0, weight=1)
        sidebar_frame.rowconfigure(2, weight=1)  # List frame gets the expansion space
        
        # Search frame
        search_frame = ttk.Frame(sidebar_frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="🔍").grid(row=0, column=0, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, font=("Segoe UI", 9))
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.search_entry.bind("<KeyRelease>", self.filter_contacts)
        
        # Sort frame
        sort_frame = ttk.Frame(sidebar_frame)
        sort_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        sort_frame.columnconfigure(1, weight=1)
        
        ttk.Label(sort_frame, text="Sort:").grid(row=0, column=0, padx=(0, 5))
        self.sort_var = tk.StringVar(value="Name A-Z")
        sort_options = ["Name A-Z", "Name Z-A", "Organization A-Z", "Organization Z-A", "Original Order"]
        self.sort_combo = ttk.Combobox(sort_frame, textvariable=self.sort_var, font=("Segoe UI", 9), 
                                      values=sort_options, state="readonly", width=15)
        self.sort_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.sort_combo.bind("<<ComboboxSelected>>", self.on_sort_change)
        
        # Map display names to sort keys
        self.sort_key_map = {
            "Name A-Z": "name_asc",
            "Name Z-A": "name_desc",
            "Organization A-Z": "org_asc", 
            "Organization Z-A": "org_desc",
            "Original Order": "original"
        }
        
        # Contact listbox with scrollbar
        list_frame = ttk.Frame(sidebar_frame)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.contact_listbox = tk.Listbox(
            list_frame, 
            font=("Segoe UI", 9),
            selectmode=tk.EXTENDED,  # Allow multiple selection
            activestyle='dotbox'
        )
        self.contact_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.contact_listbox.bind("<<ListboxSelect>>", self.on_contact_select)
        self.contact_listbox.bind("<Double-Button-1>", self.on_contact_double_click)
        self.contact_listbox.bind("<KeyPress>", self.on_listbox_key)
        self.contact_listbox.focus_set()  # Allow keyboard focus
        
        # Scrollbar for listbox
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.contact_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.contact_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # Contact count label
        self.contact_count_label = ttk.Label(sidebar_frame, text="0 contacts", font=("Segoe UI", 8))
        self.contact_count_label.grid(row=3, column=0, pady=(5, 0))
        
        # Contact action buttons
        action_frame = ttk.Frame(sidebar_frame)
        action_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        self.delete_btn = ttk.Button(action_frame, text="🗑️ Delete", command=self.delete_contacts, state=tk.DISABLED)
        self.delete_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        
        self.duplicate_btn = ttk.Button(action_frame, text="📋 Duplicate", command=self.duplicate_contact, state=tk.DISABLED)
        self.duplicate_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # Right pane - Contact preview
        preview_frame = ttk.LabelFrame(self.paned_window, text="Contact Preview", padding="5")
        self.paned_window.add(preview_frame, weight=3)  # Right pane gets more space
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        
        # Navigation controls at top of preview
        nav_frame = ttk.Frame(preview_frame)
        nav_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self.prev_card, state=tk.DISABLED)
        self.prev_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.counter_label = ttk.Label(nav_frame, text="0 / 0")
        self.counter_label.grid(row=0, column=1, padx=10)
        
        self.next_btn = ttk.Button(nav_frame, text="Next ▶", command=self.next_card, state=tk.DISABLED)
        self.next_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Jump to contact frame
        jump_frame = ttk.Frame(nav_frame)
        jump_frame.grid(row=0, column=3, padx=(20, 0))
        
        ttk.Label(jump_frame, text="Go to:").grid(row=0, column=0, padx=(0, 5))
        self.jump_entry = ttk.Entry(jump_frame, width=5)
        self.jump_entry.grid(row=0, column=1, padx=(0, 5))
        self.jump_entry.bind("<Return>", self.jump_to_card)
        ttk.Button(jump_frame, text="Go", command=self.jump_to_card).grid(row=0, column=2)
        
        # Edit controls
        edit_frame = ttk.Frame(nav_frame)
        edit_frame.grid(row=0, column=4, padx=(20, 0))
        
        self.edit_btn = ttk.Button(edit_frame, text="✏️ Edit", command=self.toggle_edit_mode, state=tk.DISABLED)
        self.edit_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.save_contact_btn = ttk.Button(edit_frame, text="💾 Save", command=self.save_contact, state=tk.DISABLED)
        self.save_contact_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Content notebook
        self.notebook = ttk.Notebook(preview_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Formatted view tab
        self.formatted_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.formatted_frame, text="Contact Details")
        self.formatted_frame.columnconfigure(0, weight=1)
        self.formatted_frame.rowconfigure(0, weight=1)
        
        self.contact_display = scrolledtext.ScrolledText(
            self.formatted_frame, 
            wrap=tk.WORD, 
            font=("Segoe UI", 10),
            state=tk.DISABLED
        )
        self.contact_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Raw vCard tab
        self.raw_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.raw_frame, text="Raw vCard")
        self.raw_frame.columnconfigure(0, weight=1)
        self.raw_frame.rowconfigure(0, weight=1)
        
        self.raw_display = scrolledtext.ScrolledText(
            self.raw_frame, 
            wrap=tk.NONE, 
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.raw_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def select_file(self):
        """Select and load a vCard file"""
        filename = filedialog.askopenfilename(
            title="Select vCard file",
            filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
        )
        
        if filename:
            self.load_vcards(filename)
            
    def load_vcards(self, filename):
        """Load vCards from file with recovery parsing for malformed data"""
        try:
            from vobject.base import ParseError
            self.current_file = filename
            self.vcards = []
            malformed = 0
            parse_errors = []
            
            with open(filename, 'r', encoding='utf-8') as f:
                data = f.read()
            
            # Try to parse individual vCards more robustly
            try:
                for v in vobject.readComponents(data):
                    try:
                        fn = getattr(v, 'fn', None)
                        if fn and fn.value.strip():
                            self.vcards.append(v)
                        else:
                            malformed += 1
                    except Exception as e:
                        malformed += 1
                        if len(parse_errors) < 5:  # Limit error collection
                            parse_errors.append(str(e)[:100])
                            
            except ParseError as e:
                # Try to recover by splitting on BEGIN:VCARD and parsing individually
                error_msg = str(e)
                parse_errors.append(error_msg[:200])
                
                # Attempt recovery parsing
                recovered = self.try_recovery_parse(data)
                self.vcards.extend(recovered)
                
                if not self.vcards and not recovered:
                    messagebox.showerror("Parse Error", 
                        f"Could not parse vCard file:\n{error_msg}\n\n"
                        "The file may be corrupted or in an unsupported format.")
                    return
            
            if not self.vcards:
                messagebox.showinfo("No Contacts", "No valid contacts found in the file.")
                return
                
            # Update UI
            self.file_label.config(text=f"{os.path.basename(filename)} ({len(self.vcards)} contacts, {malformed} malformed)")
            self.current_index = 0
            self.is_modified = False
            self.populate_contact_list()
            self.update_display()
            self.update_navigation()
            self.update_button_states()
            
            # Show summary with any parse errors
            if malformed > 0 or parse_errors:
                error_summary = f"Loaded {len(self.vcards)} contacts.\n{malformed} malformed entries were skipped."
                if parse_errors:
                    error_summary += f"\n\nSample parse errors:\n" + "\n".join(f"• {err}" for err in parse_errors[:3])
                messagebox.showinfo("Load Complete", error_summary)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def try_recovery_parse(self, data):
        """Attempt to recover parseable vCards from a corrupted file"""
        recovered = []
        
        # Split by BEGIN:VCARD and try to parse each section
        sections = data.split('BEGIN:VCARD')
        
        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            try:
                # Reconstruct a complete vCard
                vcard_text = 'BEGIN:VCARD' + section
                
                # Find the end of this vCard
                end_pos = vcard_text.find('END:VCARD')
                if end_pos == -1:
                    continue
                    
                # Extract just this vCard
                vcard_text = vcard_text[:end_pos + len('END:VCARD')]
                
                # Clean up obvious issues
                vcard_text = self.clean_vcard_text(vcard_text)
                
                # Try to parse this individual vCard
                try:
                    v = vobject.readOne(vcard_text)
                    fn = getattr(v, 'fn', None)
                    if fn and fn.value.strip():
                        recovered.append(v)
                except:
                    pass  # Skip this one
                    
            except Exception:
                pass  # Skip this section
                
        return recovered
    
    def clean_vcard_text(self, text):
        """Clean up common vCard formatting issues"""
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Skip lines that don't look like vCard properties
            if ':' not in line and not line.startswith((' ', '\t')):
                continue
                
            # Remove obvious text that got mixed in
            if any(phrase in line.lower() for phrase in [
                'this contact is read-only',
                'outlook',
                'make changes',
                'tap the li'
            ]):
                continue
                
            # Clean up escaped characters that might be malformed
            line = line.replace('\\\\', '\\')
            
            lines.append(line)
            
        return '\n'.join(lines)
    
    def export_clean_vcards(self):
        """Export vCards with corruption cleaned up"""
        if not self.vcards:
            messagebox.showwarning("No Data", "No vCards loaded to export.")
            return
            
        # Analyze corruption first
        corruption_report = self.analyze_corruption()
        
        # Ask user if they want to see the corruption report
        if messagebox.askyesno("Corruption Analysis", 
            f"Found corruption patterns in your data:\n\n{corruption_report}\n\n"
            "Would you like to export cleaned vCards that remove these issues?"):
            
            filename = filedialog.asksaveasfilename(
                title="Export Clean vCards",
                defaultextension=".vcf",
                filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
            )
            
            if filename:
                try:
                    cleaned_count = 0
                    skipped_count = 0
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        for i, card in enumerate(self.vcards):
                            try:
                                # Try to get vCard data - use multiple methods
                                raw_vcard = None
                                
                                # Method 1: Try safe serialization
                                try:
                                    raw_vcard = self.safe_serialize_vcard(card)
                                except:
                                    pass
                                
                                # Method 2: If that fails, try manual reconstruction
                                if not raw_vcard or len(raw_vcard.strip()) < 20:
                                    raw_vcard = self.manually_reconstruct_vcard(card)
                                
                                # Clean it up
                                if raw_vcard:
                                    cleaned_vcard = self.deep_clean_vcard(raw_vcard)
                                    
                                    if cleaned_vcard and len(cleaned_vcard.strip()) > 30:  # Lower threshold
                                        f.write(cleaned_vcard)
                                        f.write('\n\n')
                                        cleaned_count += 1
                                    else:
                                        print(f"Contact {i+1}: Cleaned vCard too short, attempting rescue...")
                                        # Last resort: create a minimal vCard from available data
                                        rescue_vcard = self.create_rescue_vcard(card, i+1)
                                        if rescue_vcard:
                                            f.write(rescue_vcard)
                                            f.write('\n\n')
                                            cleaned_count += 1
                                        else:
                                            skipped_count += 1
                                else:
                                    print(f"Contact {i+1}: No vCard data could be extracted")
                                    skipped_count += 1
                                    
                            except Exception as e:
                                print(f"Contact {i+1}: Exception during processing: {e}")
                                # Even if there's an exception, try to rescue what we can
                                try:
                                    rescue_vcard = self.create_rescue_vcard(card, i+1)
                                    if rescue_vcard:
                                        f.write(rescue_vcard)
                                        f.write('\n\n')
                                        cleaned_count += 1
                                    else:
                                        skipped_count += 1
                                except:
                                    skipped_count += 1
                                continue
                    
                    messagebox.showinfo("Export Complete", 
                        f"Export completed:\n"
                        f"• {cleaned_count} contacts successfully exported\n"
                        f"• {skipped_count} contacts could not be recovered\n"
                        f"• File saved to: {filename}\n\n"
                        f"Recovery rate: {(cleaned_count/(cleaned_count+skipped_count)*100):.1f}%")
                        
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export file: {e}")
    
    def manually_reconstruct_vcard(self, card):
        """Manually reconstruct a vCard from its components when serialization fails"""
        try:
            lines = ["BEGIN:VCARD", "VERSION:3.0"]
            
            # Extract basic properties manually
            fn = getattr(card, 'fn', None)
            if fn and hasattr(fn, 'value'):
                lines.append(f"FN:{fn.value}")
            
            # Try to get other common properties
            for child in card.getChildren():
                try:
                    prop_name = child.name
                    if prop_name in ['FN', 'N', 'EMAIL', 'TEL', 'ORG', 'TITLE']:
                        if hasattr(child, 'value') and child.value:
                            # Handle different value types
                            if isinstance(child.value, str):
                                value = child.value.replace('\n', '\\n').replace('\r', '')
                                lines.append(f"{prop_name}:{value}")
                            elif hasattr(child.value, '__iter__') and not isinstance(child.value, str):
                                # Handle list values
                                value_str = ';'.join(str(v) for v in child.value if v)
                                if value_str:
                                    lines.append(f"{prop_name}:{value_str}")
                except:
                    continue
            
            lines.append("END:VCARD")
            return '\n'.join(lines)
            
        except Exception as e:
            print(f"Manual reconstruction failed: {e}")
            return None
    
    def create_rescue_vcard(self, card, contact_num):
        """Create a minimal vCard as last resort"""
        try:
            fn = getattr(card, 'fn', None)
            name = fn.value if fn and hasattr(fn, 'value') else f"Contact {contact_num}"
            
            # Create absolutely minimal vCard
            rescue_lines = [
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"FN:{name}",
                "END:VCARD"
            ]
            
            return '\n'.join(rescue_lines)
        except:
            return None
    
    def analyze_corruption(self):
        """Analyze what corruption patterns exist in the loaded vCards"""
        if not hasattr(self, 'current_file') or not self.current_file:
            return "No file analysis available"
            
        try:
            with open(self.current_file, 'r', encoding='utf-8') as f:
                data = f.read()
                
            corruption_types = {
                'Outlook readonly messages': data.count('This contact is read-only'),
                'Outlook interface fragments': data.count('tap the li'),
                'Excessive escaping (backslashes)': len([line for line in data.split('\n') if line.count('\\\\') > 10]),
                'Base64 garbage lines': len([line for line in data.split('\n') if len(line) > 200 and 'gAAA' in line]),
                'Incomplete vCard sections': len([section for section in data.split('BEGIN:VCARD')[1:] if 'END:VCARD' not in section])
            }
            
            report_lines = []
            for issue_type, count in corruption_types.items():
                if count > 0:
                    report_lines.append(f"• {issue_type}: {count} instances")
                    
            return '\n'.join(report_lines) if report_lines else "No obvious corruption patterns detected"
            
        except Exception as e:
            return f"Error analyzing file: {e}"
    
    def deep_clean_vcard(self, raw_vcard):
        """Perform deep cleaning of a vCard to remove corruption"""
        if not raw_vcard or not raw_vcard.strip():
            return None
            
        lines = []
        for line in raw_vcard.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip obvious corruption patterns
            if any(corruption in line.lower() for corruption in [
                'this contact is read-only',
                'outlook',
                'make changes',
                'tap the li',
                'edit in outlook'
            ]):
                continue
                
            # Skip lines with excessive escaping
            if line.count('\\\\') > 10:
                continue
                
            # Skip lines that are clearly base64 garbage mixed in
            if len(line) > 200 and any(char in line for char in 'gAAA7l6WXMS'):
                continue
                
            # Clean up remaining escaping issues
            line = line.replace('\\\\\\\\', '\\\\')
            line = line.replace('\\\\\\', '\\')
            
            # Only include lines that look like proper vCard properties
            if (':' in line or line.startswith(('BEGIN:', 'END:', 'VERSION:', ' ', '\t'))):
                lines.append(line)
        
        # Ensure proper vCard structure
        if lines and not any(line.startswith('BEGIN:VCARD') for line in lines):
            lines.insert(0, 'BEGIN:VCARD')
        if lines and not any(line.startswith('END:VCARD') for line in lines):
            lines.append('END:VCARD')
            
        return '\n'.join(lines) if lines else None

    def on_sort_change(self, event=None):
        """Handle sort option change"""
        self.filter_contacts()  # This will apply both filtering and sorting

    def get_sort_option(self):
        """Get the current sort option key from the display value"""
        # Safety check for initialization
        if not hasattr(self, 'sort_var') or not hasattr(self, 'sort_key_map'):
            return "name_asc"  # Default fallback
            
        display_value = self.sort_var.get()
        return self.sort_key_map.get(display_value, "name_asc")

    def sort_vcards(self, vcards):
        """Sort vcards based on current sort option"""
        sort_option = self.get_sort_option()
        
        if sort_option == "original":
            return vcards
        
        def get_sort_key(card):
            if sort_option.startswith("name"):
                fn = getattr(card, 'fn', None)
                name = fn.value.strip().lower() if fn else ""
                # Handle "Last, First" format by reversing to "First Last"
                if ',' in name:
                    parts = [p.strip() for p in name.split(',', 1)]
                    if len(parts) == 2:
                        name = f"{parts[1]} {parts[0]}"
                return name
            elif sort_option.startswith("org"):
                org = getattr(card, 'org', None)
                org_name = org.value.strip().lower() if org and org.value else ""
                # If no organization, fall back to name for sorting
                if not org_name:
                    fn = getattr(card, 'fn', None)
                    org_name = fn.value.strip().lower() if fn else "zzz_no_name"
                return org_name
            return ""
        
        reverse = sort_option.endswith("_desc")
        return sorted(vcards, key=get_sort_key, reverse=reverse)

    def populate_contact_list(self):
        """Populate the contact listbox with contact names"""
        self.contact_listbox.delete(0, tk.END)
        
        # Apply sorting to all vcards
        sorted_vcards = self.sort_vcards(self.vcards)
        self.filtered_vcards = sorted_vcards.copy()
        
        for i, card in enumerate(sorted_vcards):
            # Get display name
            fn = getattr(card, 'fn', None)
            name = fn.value.strip() if fn else f"Contact {i+1}"
            
            # Add organization if available
            org = getattr(card, 'org', None)
            if org and org.value:
                name += f" ({org.value})"
                
            self.contact_listbox.insert(tk.END, name)
        
        # Update contact count
        self.contact_count_label.config(text=f"{len(self.vcards)} contacts")
        
        # Select first contact if any
        if self.vcards:
            self.contact_listbox.selection_set(0)
            self.contact_listbox.activate(0)

    def filter_contacts(self, event=None):
        """Filter contacts based on search term and apply sorting"""
        search_term = self.search_entry.get().lower()
        
        if not search_term:
            # Show all contacts with sorting applied
            self.filtered_vcards = self.sort_vcards(self.vcards)
        else:
            # Filter contacts first
            filtered = []
            for card in self.vcards:
                # Search in name
                fn = getattr(card, 'fn', None)
                name = fn.value.lower() if fn else ""
                
                # Search in organization
                org = getattr(card, 'org', None)
                org_name = org.value.lower() if org else ""
                
                # Search in email
                emails = []
                for child in card.getChildren():
                    if child.name == 'EMAIL':
                        emails.append(child.value.lower())
                email_text = " ".join(emails)
                
                if (search_term in name or 
                    search_term in org_name or 
                    search_term in email_text):
                    filtered.append(card)
            
            # Apply sorting to filtered results
            self.filtered_vcards = self.sort_vcards(filtered)
        
        # Repopulate listbox with filtered and sorted results
        self.contact_listbox.delete(0, tk.END)
        for i, card in enumerate(self.filtered_vcards):
            fn = getattr(card, 'fn', None)
            name = fn.value.strip() if fn else f"Contact {i+1}"
            
            org = getattr(card, 'org', None)
            if org and org.value:
                name += f" ({org.value})"
                
            self.contact_listbox.insert(tk.END, name)
        
        # Update contact count
        total = len(self.vcards)
        filtered = len(self.filtered_vcards)
        if filtered != total:
            self.contact_count_label.config(text=f"{filtered} of {total} contacts")
        else:
            self.contact_count_label.config(text=f"{total} contacts")
        
        # Select first filtered result if any
        if self.filtered_vcards:
            self.contact_listbox.selection_set(0)
            self.contact_listbox.activate(0)
            self.on_contact_select()

    def on_contact_select(self, event=None):
        """Handle contact selection from listbox"""
        selection = self.contact_listbox.curselection()
        if selection and self.filtered_vcards:
            index = selection[0]
            if 0 <= index < len(self.filtered_vcards):
                # Find the index in the original vcards list
                selected_card = self.filtered_vcards[index]
                self.current_index = self.vcards.index(selected_card)
                self.update_display()
                self.update_navigation()
                self.update_button_states()

    def on_contact_double_click(self, event=None):
        """Handle double-click on contact"""
        self.toggle_edit_mode()

    def on_listbox_key(self, event):
        """Handle keyboard navigation in listbox"""
        if event.keysym in ['Up', 'Down', 'Page_Up', 'Page_Down', 'Home', 'End']:
            # Let the listbox handle the navigation, then update our display
            self.root.after_idle(self.on_contact_select)
        elif event.keysym == 'Delete':
            self.delete_contacts()
        elif event.keysym == 'Return':
            self.toggle_edit_mode()

    def duplicate_contact(self):
        """Create a duplicate of the current contact"""
        if not self.filtered_vcards or self.current_index >= len(self.vcards):
            return
            
        try:
            # Get the contact to duplicate from original list
            original_card = self.vcards[self.current_index]
            
            # Create a copy by serializing and re-parsing
            vcard_text = self.safe_serialize_vcard(original_card)
            new_card = vobject.readOne(vcard_text)
            
            # Modify the name to indicate it's a copy
            fn = getattr(new_card, 'fn', None)
            if fn:
                fn.value = fn.value + " (Copy)"
                
            # Add to the list
            self.vcards.append(new_card)
            self.is_modified = True
            
            # Refresh the display
            self.populate_contact_list()
            
            # Select the new contact
            self.contact_listbox.selection_clear(0, tk.END)
            self.contact_listbox.selection_set(len(self.filtered_vcards) - 1)
            self.contact_listbox.activate(len(self.filtered_vcards) - 1)
            self.on_contact_select()
            
            messagebox.showinfo("Success", "Contact duplicated successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to duplicate contact: {e}")

    def toggle_edit_mode(self):
        """Toggle between view and edit mode for raw vCard"""
        if not self.filtered_vcards or self.current_index >= len(self.vcards):
            return
            
        if self.raw_display.cget("state") == tk.DISABLED:
            # Enter edit mode
            self.raw_display.config(state=tk.NORMAL)
            self.edit_btn.config(text="❌ Cancel")
            self.save_contact_btn.config(state=tk.NORMAL)
            # Switch to raw tab for editing
            self.notebook.select(self.raw_frame)
        else:
            # Exit edit mode
            self.raw_display.config(state=tk.DISABLED)
            self.edit_btn.config(text="✏️ Edit")
            self.save_contact_btn.config(state=tk.DISABLED)

    def save_contact(self):
        """Save changes to the current contact from raw vCard text"""
        if not self.vcards or self.current_index >= len(self.vcards):
            return
            
        try:
            # Get edited text
            raw_text = self.raw_display.get(1.0, tk.END).strip()
            
            # Parse the edited vCard
            new_card = vobject.readOne(raw_text)
            
            # Replace the current contact
            self.vcards[self.current_index] = new_card
            
            # Update displays
            self.populate_contact_list()
            self.update_display()
            self.update_navigation()
            
            # Switch back to view mode
            self.toggle_edit_mode()
            
            messagebox.showinfo("Success", "Contact updated successfully!")
            
        except Exception as e:
            messagebox.showerror("Parse Error", f"Failed to parse vCard:\n{e}\n\nPlease check the syntax and try again.")

    def safe_serialize_vcard(self, card):
        """Safely serialize a vCard, handling list values that should be strings"""
        try:
            # First try normal serialization
            return card.serialize()
        except AttributeError as e:
            if "'list' object has no attribute 'replace'" in str(e):
                # Handle the case where a property value is a list instead of string
                try:
                    # Create a copy of the card to avoid modifying the original
                    card_copy = copy.deepcopy(card)
                    
                    # Fix any list properties that should be strings
                    self._fix_list_properties(card_copy)
                    
                    return card_copy.serialize()
                except Exception as e2:
                    # If fixing fails, return a basic vCard structure
                    return self._create_fallback_vcard(card)
            else:
                raise e

    def _fix_list_properties(self, card):
        """Fix properties that are lists but should be strings"""
        for attr_name in dir(card):
            if not attr_name.startswith('_'):
                try:
                    attr = getattr(card, attr_name)
                    if hasattr(attr, 'value') and isinstance(attr.value, list):
                        # Convert list to string (join with comma for multiple values)
                        if attr.value:
                            attr.value = ', '.join(str(v) for v in attr.value if v)
                        else:
                            attr.value = ''
                except (AttributeError, TypeError):
                    continue

    def _create_fallback_vcard(self, original_card):
        """Create a minimal vCard if serialization completely fails"""
        try:
            name = getattr(original_card, 'fn', None)
            if name and hasattr(name, 'value'):
                fn_value = name.value if isinstance(name.value, str) else str(name.value)
            else:
                fn_value = "Unknown Contact"
                
            return f"BEGIN:VCARD\nVERSION:3.0\nFN:{fn_value}\nEND:VCARD\n"
        except:
            return "BEGIN:VCARD\nVERSION:3.0\nFN:Unknown Contact\nEND:VCARD\n"

    def save_as_file(self):
        """Save contacts to a new file"""
        filename = filedialog.asksaveasfilename(
            title="Save vCard file as...",
            defaultextension=".vcf",
            filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for card in self.vcards:
                        serialized = self.safe_serialize_vcard(card)
                        f.write(serialized)
                        
                self.current_file = filename
                self.is_modified = False
                self.update_title()
                self.file_label.config(text=f"{os.path.basename(filename)} ({len(self.vcards)} contacts)")
                messagebox.showinfo("Success", f"Saved {len(self.vcards)} contacts to {os.path.basename(filename)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def update_title(self):
        """Update window title to show modification status"""
        title = "vCard Viewer"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
            if self.is_modified:
                title += " *"
        self.root.title(title)

    def delete_contacts(self):
        """Delete selected contacts"""
        selection = self.contact_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select one or more contacts to delete.")
            return
            
        # Get selected contacts from filtered list
        selected_cards = [self.filtered_vcards[i] for i in selection]
        
        # Confirm deletion
        count = len(selected_cards)
        if count == 1:
            message = "Are you sure you want to delete this contact?"
        else:
            message = f"Are you sure you want to delete these {count} contacts?"
            
        if messagebox.askyesno("Confirm Deletion", message):
            try:
                # Remove from original list
                for card in selected_cards:
                    self.vcards.remove(card)
                
                self.is_modified = True
                
                # Refresh display
                self.populate_contact_list()
                
                # Update current index
                if self.vcards:
                    self.current_index = min(self.current_index, len(self.vcards) - 1)
                    if self.filtered_vcards:
                        # Select the next contact
                        new_selection = min(selection[0], len(self.filtered_vcards) - 1)
                        self.contact_listbox.selection_set(new_selection)
                        self.contact_listbox.activate(new_selection)
                        self.on_contact_select()
                    else:
                        self.current_index = -1
                        self.update_display()
                        self.update_navigation()
                else:
                    self.current_index = -1
                    self.update_display()
                    self.update_navigation()
                
                self.update_button_states()
                
                if count == 1:
                    messagebox.showinfo("Success", "Contact deleted successfully!")
                else:
                    messagebox.showinfo("Success", f"{count} contacts deleted successfully!")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete contact(s): {e}")

    def update_display(self):
        """Update the contact display with current contact"""
        if not self.filtered_vcards or self.current_index < 0 or self.current_index >= len(self.vcards):
            # Clear displays
            self.contact_display.config(state=tk.NORMAL)
            self.contact_display.delete(1.0, tk.END)
            self.contact_display.insert(tk.END, "No contact selected")
            self.contact_display.config(state=tk.DISABLED)
            
            self.raw_display.config(state=tk.NORMAL)
            self.raw_display.delete(1.0, tk.END)
            self.raw_display.insert(tk.END, "No contact selected")
            self.raw_display.config(state=tk.DISABLED)
            return
            
        # Get current contact from original vcards list
        card = self.vcards[self.current_index]
        
        # Update formatted display
        self.contact_display.config(state=tk.NORMAL)
        self.contact_display.delete(1.0, tk.END)
        formatted_text = self.format_contact(card)
        self.contact_display.insert(tk.END, formatted_text)
        self.contact_display.config(state=tk.DISABLED)
        
        # Update raw display
        self.raw_display.config(state=tk.NORMAL)
        self.raw_display.delete(1.0, tk.END)
        self.raw_display.insert(tk.END, self.safe_serialize_vcard(card))
        self.raw_display.config(state=tk.DISABLED)
        
    def format_contact(self, card):
        """Format a vCard into a readable contact display"""
        lines = []
        
        # Name
        fn = getattr(card, 'fn', None)
        if fn:
            lines.append(f"📛 Name: {fn.value}")
            
        # Organization
        org = getattr(card, 'org', None)
        if org and org.value:
            lines.append(f"🏢 Organization: {org.value}")
            
        # Title
        title = getattr(card, 'title', None)
        if title and title.value:
            lines.append(f"💼 Title: {title.value}")
            
        # Phone numbers
        phones = []
        for child in card.getChildren():
            if child.name == 'TEL':
                phone_type = ', '.join(child.params.get('TYPE', ['Phone']))
                phones.append(f"📞 {phone_type}: {child.value}")
        if phones:
            lines.extend(phones)
            
        # Email addresses
        emails = []
        for child in card.getChildren():
            if child.name == 'EMAIL':
                email_type = ', '.join(child.params.get('TYPE', ['Email']))
                emails.append(f"📧 {email_type}: {child.value}")
        if emails:
            lines.extend(emails)
            
        # Addresses
        addresses = []
        for child in card.getChildren():
            if child.name == 'ADR':
                addr_type = ', '.join(child.params.get('TYPE', ['Address']))
                # Address format: PO Box, Extended, Street, City, State, ZIP, Country
                try:
                    # Handle both string values and Address objects
                    if hasattr(child.value, 'split'):
                        addr_parts = child.value.split(';')
                    else:
                        # For Address objects, convert to string first
                        addr_str = str(child.value) if child.value else ''
                        addr_parts = addr_str.split(';')
                    
                    formatted_addr = []
                    if len(addr_parts) > 2 and addr_parts[2]:  # Street
                        formatted_addr.append(addr_parts[2])
                    if len(addr_parts) > 3 and addr_parts[3]:  # City
                        formatted_addr.append(addr_parts[3])
                    if len(addr_parts) > 4 and addr_parts[4]:  # State
                        formatted_addr.append(addr_parts[4])
                    if len(addr_parts) > 5 and addr_parts[5]:  # ZIP
                        formatted_addr.append(addr_parts[5])
                        
                    if formatted_addr:
                        addresses.append(f"🏠 {addr_type}: {', '.join(formatted_addr)}")
                except Exception:
                    # Fallback for any address parsing issues
                    addr_str = str(child.value) if child.value else 'Unknown address'
                    addresses.append(f"🏠 {addr_type}: {addr_str}")
                    
        if addresses:
            lines.extend(addresses)
            
        # Notes
        note = getattr(card, 'note', None)
        if note and note.value:
            lines.append(f"📝 Note: {note.value}")
            
        # Birthday
        bday = getattr(card, 'bday', None)
        if bday and bday.value:
            lines.append(f"🎂 Birthday: {bday.value}")
            
        # URL
        url = getattr(card, 'url', None)
        if url and url.value:
            lines.append(f"🌐 Website: {url.value}")
            
        return '\n'.join(lines) if lines else "No contact information available"

    def update_navigation(self):
        """Update navigation buttons and counter"""
        if not self.filtered_vcards:
            self.counter_label.config(text="0 / 0")
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            return
            
        # Find current contact in filtered list
        current_card = self.vcards[self.current_index] if self.current_index < len(self.vcards) else None
        if current_card in self.filtered_vcards:
            filtered_index = self.filtered_vcards.index(current_card) + 1
        else:
            filtered_index = 0
            
        total = len(self.filtered_vcards)
        self.counter_label.config(text=f"{filtered_index} / {total}")
        
        # Update button states
        self.prev_btn.config(state=tk.NORMAL if filtered_index > 1 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if filtered_index < total else tk.DISABLED)

    def update_button_states(self):
        """Update button states based on current selection"""
        has_selection = bool(self.contact_listbox.curselection())
        has_contacts = bool(self.filtered_vcards)
        
        # Edit/navigation buttons
        state = tk.NORMAL if has_contacts else tk.DISABLED
        self.edit_btn.config(state=state)
        self.duplicate_btn.config(state=state)
        
        # Delete button (depends on selection)
        self.delete_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)

    def prev_card(self):
        """Navigate to previous contact"""
        if not self.filtered_vcards:
            return
            
        current_card = self.vcards[self.current_index] if self.current_index < len(self.vcards) else None
        if current_card in self.filtered_vcards:
            filtered_index = self.filtered_vcards.index(current_card)
            if filtered_index > 0:
                # Select previous contact in filtered list
                new_filtered_index = filtered_index - 1
                new_card = self.filtered_vcards[new_filtered_index]
                self.current_index = self.vcards.index(new_card)
                
                # Update listbox selection
                self.contact_listbox.selection_clear(0, tk.END)
                self.contact_listbox.selection_set(new_filtered_index)
                self.contact_listbox.activate(new_filtered_index)
                self.contact_listbox.see(new_filtered_index)
                
                self.update_display()
                self.update_navigation()

    def next_card(self):
        """Navigate to next contact"""
        if not self.filtered_vcards:
            return
            
        current_card = self.vcards[self.current_index] if self.current_index < len(self.vcards) else None
        if current_card in self.filtered_vcards:
            filtered_index = self.filtered_vcards.index(current_card)
            if filtered_index < len(self.filtered_vcards) - 1:
                # Select next contact in filtered list
                new_filtered_index = filtered_index + 1
                new_card = self.filtered_vcards[new_filtered_index]
                self.current_index = self.vcards.index(new_card)
                
                # Update listbox selection
                self.contact_listbox.selection_clear(0, tk.END)
                self.contact_listbox.selection_set(new_filtered_index)
                self.contact_listbox.activate(new_filtered_index)
                self.contact_listbox.see(new_filtered_index)
                
                self.update_display()
                self.update_navigation()

    def jump_to_card(self, event=None):
        """Jump to a specific contact number"""
        try:
            target = int(self.jump_entry.get())
            if 1 <= target <= len(self.filtered_vcards):
                # Convert to 0-based index
                filtered_index = target - 1
                new_card = self.filtered_vcards[filtered_index]
                self.current_index = self.vcards.index(new_card)
                
                # Update listbox selection
                self.contact_listbox.selection_clear(0, tk.END)
                self.contact_listbox.selection_set(filtered_index)
                self.contact_listbox.activate(filtered_index)
                self.contact_listbox.see(filtered_index)
                
                self.update_display()
                self.update_navigation()
                
                # Clear jump entry
                self.jump_entry.delete(0, tk.END)
            else:
                messagebox.showwarning("Invalid Number", f"Please enter a number between 1 and {len(self.filtered_vcards)}")
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")


def main():
    root = tk.Tk()
    app = VCardViewer(root)
    
    # Handle window closing
    def on_closing():
        if app.is_modified:
            if messagebox.askyesnocancel("Unsaved Changes", "You have unsaved changes. Do you want to save before closing?"):
                app.save_as_file()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
