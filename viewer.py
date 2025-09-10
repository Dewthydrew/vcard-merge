#!/usr/bin/env python3
"""
Simple vCard Viewer - Browse through vCard contacts with a GUI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import vobject
from vobject.base import ParseError
import os


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
        main_frame.columnconfigure(1, weight=3)  # Right pane gets more space
        main_frame.rowconfigure(1, weight=1)    # Main content area
        
        # File selection frame (spans both columns)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Select vCard File", command=self.select_file).grid(row=0, column=0, padx=(0, 10))
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # File action buttons
        ttk.Button(file_frame, text="Save", command=self.save_file).grid(row=0, column=2, padx=(10, 5))
        ttk.Button(file_frame, text="Save As...", command=self.save_as_file).grid(row=0, column=3, padx=(5, 0))
        
        # Left sidebar - Contact list
        sidebar_frame = ttk.LabelFrame(main_frame, text="Contacts", padding="5")
        sidebar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        sidebar_frame.columnconfigure(0, weight=1)
        sidebar_frame.rowconfigure(1, weight=1)
        
        # Search box in sidebar
        search_frame = ttk.Frame(sidebar_frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="🔍").grid(row=0, column=0, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, font=("Segoe UI", 9))
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.search_entry.bind("<KeyRelease>", self.filter_contacts)
        
        # Contact listbox with scrollbar
        list_frame = ttk.Frame(sidebar_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.contact_listbox = tk.Listbox(
            list_frame, 
            font=("Segoe UI", 9),
            selectmode=tk.SINGLE,
            activestyle='dotbox'
        )
        self.contact_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.contact_listbox.bind("<<ListboxSelect>>", self.on_contact_select)
        self.contact_listbox.bind("<Double-Button-1>", self.on_contact_double_click)
        
        # Scrollbar for listbox
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.contact_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.contact_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # Contact count label
        self.contact_count_label = ttk.Label(sidebar_frame, text="0 contacts", font=("Segoe UI", 8))
        self.contact_count_label.grid(row=2, column=0, pady=(5, 0))
        
        # Contact action buttons
        action_frame = ttk.Frame(sidebar_frame)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        self.delete_btn = ttk.Button(action_frame, text="🗑️ Delete", command=self.delete_contact, state=tk.DISABLED)
        self.delete_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        
        self.duplicate_btn = ttk.Button(action_frame, text="📋 Duplicate", command=self.duplicate_contact, state=tk.DISABLED)
        self.duplicate_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # Right pane - Contact preview
        preview_frame = ttk.LabelFrame(main_frame, text="Contact Preview", padding="5")
        preview_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
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
            wrap=tk.WORD, 
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.raw_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.raw_display.bind("<KeyRelease>", self.on_raw_edit)
        
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Select vCard file",
            filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
        )
        
        if filename:
            self.load_vcards(filename)
            
    def load_vcards(self, filename):
        try:
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

    def update_button_states(self):
        """Update button states based on current context"""
        has_contacts = bool(self.vcards)
        self.delete_btn.config(state=tk.NORMAL if has_contacts else tk.DISABLED)
        self.duplicate_btn.config(state=tk.NORMAL if has_contacts else tk.DISABLED)
        self.edit_btn.config(state=tk.NORMAL if has_contacts else tk.DISABLED)

    def populate_contact_list(self):
        """Populate the contact listbox with contact names"""
        self.contact_listbox.delete(0, tk.END)
        self.filtered_vcards = self.vcards.copy()
        
        for i, card in enumerate(self.vcards):
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
        """Filter contacts based on search term"""
        search_term = self.search_entry.get().lower()
        
        if not search_term:
            # Show all contacts
            self.filtered_vcards = self.vcards.copy()
        else:
            # Filter contacts
            self.filtered_vcards = []
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
                    self.filtered_vcards.append(card)
        
        # Repopulate listbox with filtered results
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
            list_index = selection[0]
            if 0 <= list_index < len(self.filtered_vcards):
                # Find the actual index in the full vcards list
                selected_card = self.filtered_vcards[list_index]
                self.current_index = self.vcards.index(selected_card)
                self.update_display()
                self.update_navigation()

    def on_contact_double_click(self, event=None):
        """Handle double-click on contact (could add additional actions)"""
        self.on_contact_select(event)
        # Could add: copy to clipboard, edit contact, etc.

    def delete_contact(self):
        """Delete the currently selected contact"""
        if not self.vcards or self.current_index >= len(self.vcards):
            return
            
        # Get contact name for confirmation
        card = self.vcards[self.current_index]
        fn = getattr(card, 'fn', None)
        name = fn.value.strip() if fn else f"Contact {self.current_index + 1}"
        
        # Confirm deletion
        if messagebox.askyesno("Delete Contact", f"Are you sure you want to delete '{name}'?"):
            # Remove from main list
            del self.vcards[self.current_index]
            self.is_modified = True
            
            # Adjust current index
            if self.current_index >= len(self.vcards) and self.vcards:
                self.current_index = len(self.vcards) - 1
            elif not self.vcards:
                self.current_index = 0
                
            # Update UI
            self.populate_contact_list()
            self.update_display()
            self.update_navigation()
            self.update_button_states()
            self.update_title()

    def duplicate_contact(self):
        """Duplicate the currently selected contact"""
        if not self.vcards or self.current_index >= len(self.vcards):
            return
            
        try:
            # Get current contact
            original_card = self.vcards[self.current_index]
            
            # Create a copy by serializing and re-parsing
            vcard_text = original_card.serialize()
            new_card = vobject.readOne(vcard_text)
            
            # Modify the name to indicate it's a copy
            fn = getattr(new_card, 'fn', None)
            if fn:
                fn.value = fn.value + " (Copy)"
                
            # Insert after current contact
            self.vcards.insert(self.current_index + 1, new_card)
            self.is_modified = True
            
            # Move to the new contact
            self.current_index += 1
            
            # Update UI
            self.populate_contact_list()
            self.update_display()
            self.update_navigation()
            self.update_title()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to duplicate contact: {e}")

    def toggle_edit_mode(self):
        """Toggle between view and edit mode for raw vCard data"""
        current_state = self.raw_display.cget('state')
        
        if current_state == tk.DISABLED:
            # Enable editing
            self.raw_display.config(state=tk.NORMAL)
            self.edit_btn.config(text="👁️ View")
            self.save_contact_btn.config(state=tk.NORMAL)
        else:
            # Disable editing (view mode)
            self.raw_display.config(state=tk.DISABLED)
            self.edit_btn.config(text="✏️ Edit")
            self.save_contact_btn.config(state=tk.DISABLED)

    def on_raw_edit(self, event=None):
        """Handle changes to raw vCard text"""
        if self.raw_display.cget('state') == tk.NORMAL:
            self.is_modified = True
            self.update_title()

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

    def save_file(self):
        """Save changes to the current file"""
        if not self.current_file:
            self.save_as_file()
            return
            
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                for card in self.vcards:
                    f.write(card.serialize())
                    
            self.is_modified = False
            self.update_title()
            messagebox.showinfo("Success", f"Saved {len(self.vcards)} contacts to {os.path.basename(self.current_file)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

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
                        f.write(card.serialize())
                        
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
            
    def update_display(self):
        if not self.vcards:
            return
            
        card = self.vcards[self.current_index]
        
        # Update formatted display
        self.contact_display.config(state=tk.NORMAL)
        self.contact_display.delete(1.0, tk.END)
        self.contact_display.insert(tk.END, self.format_contact(card))
        self.contact_display.config(state=tk.DISABLED)
        
        # Update raw display
        self.raw_display.config(state=tk.NORMAL)
        self.raw_display.delete(1.0, tk.END)
        self.raw_display.insert(tk.END, card.serialize())
        self.raw_display.config(state=tk.DISABLED)
        
    def format_contact(self, card):
        """Format a vCard into a readable contact display"""
        lines = []
        
        # Name
        fn = getattr(card, 'fn', None)
        if fn:
            lines.append(f"📋 Name: {fn.value}")
            
        # Structured name
        n = getattr(card, 'n', None)
        if n and hasattr(n, 'value'):
            try:
                name_parts = n.value
                if len(name_parts) >= 2:
                    lines.append(f"   Given: {name_parts[1] or '(none)'}")
                    lines.append(f"   Family: {name_parts[0] or '(none)'}")
                if len(name_parts) >= 3 and name_parts[2]:
                    lines.append(f"   Middle: {name_parts[2]}")
                if len(name_parts) >= 4 and name_parts[3]:
                    lines.append(f"   Prefix: {name_parts[3]}")
                if len(name_parts) >= 5 and name_parts[4]:
                    lines.append(f"   Suffix: {name_parts[4]}")
            except:
                pass
                
        lines.append("")  # Empty line
        
        # Organization
        org = getattr(card, 'org', None)
        if org:
            lines.append(f"🏢 Organization: {org.value}")
            
        title = getattr(card, 'title', None)
        if title:
            lines.append(f"💼 Title: {title.value}")
            
        if org or title:
            lines.append("")
            
        # Contact info
        emails = []
        phones = []
        urls = []
        addresses = []
        
        for child in card.getChildren():
            if child.name == 'EMAIL':
                email_type = ', '.join(child.params.get('TYPE', [''])) if 'TYPE' in child.params else ''
                type_str = f" ({email_type})" if email_type else ""
                emails.append(f"   📧 {child.value}{type_str}")
                
            elif child.name == 'TEL':
                tel_type = ', '.join(child.params.get('TYPE', [''])) if 'TYPE' in child.params else ''
                type_str = f" ({tel_type})" if tel_type else ""
                phones.append(f"   📞 {child.value}{type_str}")
                
            elif child.name == 'URL':
                urls.append(f"   🌐 {child.value}")
                
            elif child.name == 'ADR':
                addr_type = ', '.join(child.params.get('TYPE', [''])) if 'TYPE' in child.params else ''
                type_str = f" ({addr_type})" if addr_type else ""
                try:
                    addr_parts = child.value
                    addr_str = ', '.join(part for part in addr_parts if part)
                    addresses.append(f"   🏠 {addr_str}{type_str}")
                except:
                    addresses.append(f"   🏠 {str(child.value)}{type_str}")
        
        if emails:
            lines.append("Email Addresses:")
            lines.extend(emails)
            lines.append("")
            
        if phones:
            lines.append("Phone Numbers:")
            lines.extend(phones)
            lines.append("")
            
        if addresses:
            lines.append("Addresses:")
            lines.extend(addresses)
            lines.append("")
            
        if urls:
            lines.append("URLs:")
            lines.extend(urls)
            lines.append("")
            
        # Other fields
        other_fields = []
        for child in card.getChildren():
            if child.name not in ['VERSION', 'FN', 'N', 'ORG', 'TITLE', 'EMAIL', 'TEL', 'URL', 'ADR']:
                try:
                    value = str(child.value) if hasattr(child, 'value') else str(child)
                    if len(value) > 100:
                        value = value[:97] + "..."
                    other_fields.append(f"   {child.name}: {value}")
                except:
                    other_fields.append(f"   {child.name}: (complex value)")
                    
        if other_fields:
            lines.append("Other Fields:")
            lines.extend(other_fields)
            
        return '\n'.join(lines)
        
    def update_navigation(self):
        total = len(self.vcards)
        current = self.current_index + 1 if self.vcards else 0
        
        self.counter_label.config(text=f"{current} / {total}")
        
        self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_index < total - 1 else tk.DISABLED)
        
        # Update listbox selection to match current contact
        if self.vcards and hasattr(self, 'contact_listbox'):
            current_card = self.vcards[self.current_index]
            try:
                filtered_index = self.filtered_vcards.index(current_card)
                self.contact_listbox.selection_clear(0, tk.END)
                self.contact_listbox.selection_set(filtered_index)
                self.contact_listbox.activate(filtered_index)
                self.contact_listbox.see(filtered_index)  # Scroll to show selection
            except ValueError:
                # Current card not in filtered list, clear selection
                self.contact_listbox.selection_clear(0, tk.END)
        
    def prev_card(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
            self.update_navigation()
            
    def next_card(self):
        if self.current_index < len(self.vcards) - 1:
            self.current_index += 1
            self.update_display()
            self.update_navigation()
            
    def jump_to_card(self, event=None):
        try:
            target = int(self.jump_entry.get()) - 1  # Convert to 0-based index
            if 0 <= target < len(self.vcards):
                self.current_index = target
                self.update_display()
                self.update_navigation()
                self.jump_entry.delete(0, tk.END)
            else:
                messagebox.showwarning("Invalid Number", f"Please enter a number between 1 and {len(self.vcards)}")
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")


def main():
    root = tk.Tk()
    app = VCardViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
