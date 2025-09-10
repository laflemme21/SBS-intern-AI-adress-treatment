import sys, os
sys.path.insert(0, os.path.dirname(__file__))# Ensure local modules are found when using embedded Python

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog 
import json
import os
import traceback
from backend_main import backend_main 

CONFIG_PATH = "ressources/config.json"
SCHEMA_PATH = "ressources/schema.json"

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(path, config):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class FunctionsEditor(tk.Frame):
    def __init__(self, master, config, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config = config
        self.vars = {}
        self.build_ui()

    def build_ui(self):
        functions = self.config.get("functions", {})
        row = 0
        for key, value in functions.items():
            var = tk.BooleanVar(value=value)
            self.vars[key] = var
            chk = ttk.Checkbutton(self, text=key, variable=var)
            chk.grid(row=row, column=0, sticky="w", padx=10, pady=5)
            var.trace_add("write", lambda *args, k=key: self.on_toggle(k))
            row += 1

        # Open parameters button: closes this window and opens the parameters window
        open_params_btn = ttk.Button(self, text="Next", command=self.open_params_window)
        open_params_btn.grid(row=row, column=0, pady=6, sticky="w")
        row += 1

        # Close button (no save on exit)
        close_btn = ttk.Button(self, text="Close", command=self.close_without_saving)
        close_btn.grid(row=row, column=0, pady=10, sticky="w")

    def close_without_saving(self):
        # Do not persist toggles, simply close the first page
        self.winfo_toplevel().destroy()

    def save_functions_into_config(self):
        # Helper to persist current toggles into self.config["functions"]
        self.config["functions"] = {k: v.get() for k, v in self.vars.items()}

    def open_params_window(self):
        # Close first page and open the second; do NOT save to disk here
        selected_groups = [k for k, v in self.vars.items() if v.get()]
        # Persist toggles in-memory so the second page can use them
        self.save_functions_into_config()

        # Destroy the first window
        self.winfo_toplevel().destroy()

        # Load schema and start the parameters window
        try:
            schema = load_schema(SCHEMA_PATH)
        except Exception as e:
            # If schema can't be loaded, still exit cleanly
            tk.Tk().withdraw()
            error_text = traceback.format_exc()
            show_selectable_error("Error", f"Failed to load schema: {error_text}")
            return

        start_parameters_window(self.config, schema, selected_groups)

    def on_toggle(self, changed_key):
        # Example policies tying features together
        if changed_key == "use_mistral" and self.vars["use_mistral"].get():
            self.vars["parse_and_save_batch_ans_file"].set(False)
            self.vars["log_statistics"].set(True)
            self.vars["save_answers"].set(True)
            self.vars["calculate_conf_score"].set(True)
            self.vars["build_and_save_prompts"].set(False)

        if changed_key == "log_statistics" and self.vars["log_statistics"].get():
            self.vars["use_mistral"].set(True)
            self.vars["parse_and_save_batch_ans_file"].set(False)
            self.vars["save_answers"].set(True)
            self.vars["calculate_conf_score"].set(True)
            self.vars["build_and_save_prompts"].set(False)

        if changed_key == "parse_and_save_batch_ans_file" and self.vars["parse_and_save_batch_ans_file"].get():
            self.vars["use_mistral"].set(False)
            self.vars["log_statistics"].set(False)
            self.vars["build_and_save_prompts"].set(False)
            self.vars["calculate_conf_score"].set(True)

        if changed_key == "build_and_save_prompts" and self.vars["build_and_save_prompts"].get():
            self.vars["use_mistral"].set(False)
            self.vars["log_statistics"].set(False)
            self.vars["parse_and_save_batch_ans_file"].set(False)
            self.vars["calculate_conf_score"].set(False)
            self.vars["save_answers"].set(False)
            self.vars["check_postal_code"].set(False)
            self.vars["check_ville"].set(False)

        if changed_key == "save_answers" and self.vars["save_answers"].get():
            # Force at least one producer for answers
            if not (self.vars["use_mistral"].get() or self.vars["parse_and_save_batch_ans_file"].get()):
                self.vars["parse_and_save_batch_ans_file"].set(True)

class ParametersWindow(tk.Toplevel):
    """
    Second page. Displays and allows editing of config parameters whose schema nodes have x-group
    intersecting with the selected function flags. Provides 'Previous', 'Save', and 'Run' controls.
    """
    def __init__(self, master, config, schema, selected_groups):
        super().__init__(master)
        self.title("Selected Parameters")
        self.config_obj = config
        self.schema = schema
        self.selected_groups = set(selected_groups)
        self.field_vars = {}
        self.entry_widgets = []
        self.max_display_chars = 150
        self.max_input_chars = 512

        # Track binding state
        self._mousewheel_bound = False

        # Ensure closing the window terminates the app
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        self.canvas = canvas
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.fields_frame = ttk.Frame(canvas)

        self.fields_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.fields_frame, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Make the whole page scrollable (bind global wheel events)
        self._bind_mousewheel()

        # First pass: collect fields and compute the longest display value
        fields_to_render = []
        longest_content_chars = 0  # renamed from max_len
        for path, node, xgroups in self._iter_leaf_nodes_with_xgroup():
            if not xgroups or self.selected_groups.isdisjoint(xgroups):
                continue
            current = self._get_from_config(path)
            display = self._value_to_display(node, current)
            longest_content_chars = max(longest_content_chars, len(display))
            fields_to_render.append((path, node, display))

        # Decide unified entry width (characters), with a sensible cap
        self.entry_char_width = max(20, min(longest_content_chars + 2, self.max_display_chars))

        # Second pass: render with unified width and align all inputs
        rows = 0
        self.link_map = self._build_xlink_map()
        for path, node, display in fields_to_render:
            label_text = " / ".join(path)
            ttk.Label(self.fields_frame, text=label_text).grid(row=rows, column=0, padx=6, pady=4, sticky="w")

            tk_var = tk.StringVar(value=display)
            entry = ttk.Entry(self.fields_frame, textvariable=tk_var, width=self.entry_char_width)
            entry.grid(row=rows, column=1, padx=6, pady=4, sticky="ew")
            self.entry_widgets.append(entry)
            self.field_vars[tuple(path)] = (tk_var, node)

            # Keep all inputs same size and enforce max input length
            tk_var.trace_add("write", lambda *_, v=tk_var, p=tuple(path): self._on_var_changed(v, p))

            # add a Browse… button for suitable fields
            if self._should_add_browse(node, path):
                browse_text = "Browse…"
                ttk.Button(
                    self.fields_frame,
                    text=browse_text,
                    command=lambda v=tk_var, n=node, p=path: self._browse_for_value(v, n, p)
                ).grid(row=rows, column=2, padx=6, pady=4, sticky="w")

            rows += 1

        # Align columns
        self.fields_frame.columnconfigure(0, weight=0)
        self.fields_frame.columnconfigure(1, weight=1)

        # Buttons row (Previous | Save | Run)
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="Run", command=self._run).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._apply_and_save).pack(side="right", padx=6)
        ttk.Button(btns, text="Previous", command=self._previous).pack(side="right", padx=6)

        # Resize window to favor height over width
        self._resize_to_content()

    def _build_xlink_map(self):
        """
        Build a mapping from each field path to its linked field paths using x-link in the schema.
        Returns: {tuple(path): [tuple(linked_path), ...], ...}
        """
        xlink_map = {}
        for path, node, _ in self._iter_leaf_nodes_with_xgroup():
            links = node.get("x-link", [])
            if isinstance(links, list):
                # Each link is a list of keys representing a path
                xlink_map[tuple(path)] = [tuple(l) for l in links if isinstance(l, list)]
        return xlink_map

    def _on_var_changed(self, tk_var: tk.StringVar, changed_path=None):
        # Enforce max input content length
        text = tk_var.get() or ""
        if len(text) > self.max_input_chars:
            tk_var.set(text[:self.max_input_chars])
            text = tk_var.get()

        # Synchronize linked fields using x-link
        if changed_path and changed_path in self.link_map:
            for linked_path in self.link_map[changed_path]:
                if linked_path in self.field_vars:
                    linked_var, _ = self.field_vars[linked_path]
                    if linked_var.get() != text:
                        linked_var.set(text)

        # Grow unified width up to display cap if needed
        if len(text) > self.entry_char_width and self.entry_char_width < self.max_display_chars:
            self.entry_char_width = min(len(text) + 2, self.max_display_chars)
            for e in self.entry_widgets:
                e.configure(width=self.entry_char_width)
            self._resize_to_content()

    def _resize_to_content(self):
        self.update_idletasks()
        req_w = self.fields_frame.winfo_reqwidth()
        req_h = self.fields_frame.winfo_reqheight()

        # Clamp dimensions
        width = max(520, min(req_w , 1100)+90)    # add extra width for browse button
        height = max(520, min(req_h +180, 700))  # favor taller window

        self.geometry(f"{width}x{height}")
        try:
            self.canvas.configure(width=width - 40, height=height - 200)
        except Exception:
            pass

    # Mouse wheel bindings (scroll anywhere in window)
    def _bind_mousewheel(self):
        if self._mousewheel_bound:
            return
        # Windows/macOS
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        # Linux (X11)
        self.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")
        self._mousewheel_bound = True

    def _unbind_mousewheel(self):
        if not self._mousewheel_bound:
            return
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        finally:
            self._mousewheel_bound = False

    def _on_mousewheel(self, event):
        # Negative delta scrolls down; 120 is one notch on Windows
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta != 0:
            self.canvas.yview_scroll(delta, "units")
        return "break"

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        return "break"

    def _should_add_browse(self, node: dict, path: list[str]) -> bool:
        """
        Show a Browse… button only if the field name contains 'file'.
        """
        name = (path[-1] if path else "")
        return "file" in name.lower()
    

    def _browse_for_value(self, tk_var, node, path):
        """
        Open a file dialog and set the selected path(s) to the entry.
        """
        t = node.get("type")
        # Decide dialog type
        if t == "string":
            chosen = filedialog.askopenfilename(title="Select file")
            if chosen:
                tk_var.set(chosen)
        elif t == "array":
            chosen = filedialog.askopenfilenames(title="Select files")
            if chosen:
                tk_var.set(",".join(chosen))

    def _on_close(self):
        # Unbind wheel and terminate hidden root
        self._unbind_mousewheel()
        try:
            self.destroy()
        finally:
            try:
                self.master.destroy()
            except Exception:
                pass

    def _iter_leaf_nodes_with_xgroup(self):
        # Traverse schema properties to yield leaf fields with x-group
        def walk(node, path):
            node_type = node.get("type")
            if node_type == "object" and "properties" in node:
                for name, sub in node["properties"].items():
                    yield from walk(sub, path + [name])
            else:
                xg = node.get("x-group", [])
                if isinstance(xg, str):
                    xg = [xg]
                yield (path, node, set(xg))

        for top_name, top_node in (self.schema.get("properties") or {}).items():
            if top_name == "functions":
                continue
            yield from walk(top_node, [top_name])

    def _value_to_display(self, node, current):
        t = node.get("type")
        if t == "array":
            item_t = (node.get("items") or {}).get("type", "string")
            if isinstance(current, list):
                if item_t in ("number", "integer"):
                    return ",".join(str(x) for x in current)
                return ",".join("" if x is None else str(x) for x in current)
            return "" if current is None else str(current)
        return "" if current is None else str(current)

    def _get_from_config(self, path):
        d = self.config_obj
        for key in path:
            if not isinstance(d, dict) or key not in d:
                return None
            d = d[key]
        return d

    def _set_in_config(self, path, value):
        d = self.config_obj
        for key in path[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        d[path[-1]] = value

    def _convert_value(self, text, node):
        t = node.get("type")
        if t == "integer":
            try:
                return int(text)
            except Exception:
                return None
        if t == "number":
            try:
                return float(text)
            except Exception:
                return None
        if t == "array":
            item_t = (node.get("items") or {}).get("type", "string")
            items = [s.strip() for s in text.split(",")] if text.strip() else []
            if item_t == "integer":
                out = []
                for s in items:
                    try:
                        out.append(int(s))
                    except Exception:
                        pass
                return out
            if item_t == "number":
                out = []
                for s in items:
                    try:
                        out.append(float(s))
                    except Exception:
                        pass
                return out
            return items
        return text

    def _apply_and_save(self):
        # Write back edited values into config
        for path, (tk_var, node) in self.field_vars.items():
            raw = tk_var.get()
            value = self._convert_value(raw, node)
            self._set_in_config(list(path), value)
        try:
            save_config(CONFIG_PATH, self.config_obj)
            messagebox.showinfo("Success", "Parameters saved to ressources/config.json.")
        except Exception as e:
            error_text = traceback.format_exc()
            show_selectable_error("Error", f"Failed to save config: {error_text}")

    def _run(self):
        # Apply edits and save to ressources/config.json (represents 'Run' action placeholder)
        self._apply_and_save()
        messagebox.showinfo("Run", "Running program with current configuration...\n(the app will terminate after the program finishes)")

        # Disable window close (make unterminatable by user)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        try:
            backend_main()
        except Exception as e:
            error_text = traceback.format_exc()
            err_win = show_selectable_error("Error", f"An error occurred during execution: {error_text}")
            self.wait_window(err_win)
        finally:
            root = self.master
            try:
                self.destroy()
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass


    def _previous(self):
        # Close this page and return to first page without saving more changes
        # Destroy this Toplevel and its hidden root, then reopen FunctionsEditor
        root = self.master
        try:
            self.destroy()
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        start_functions_window(self.config_obj)

def show_selectable_error(title, error_text):
    # Show error in a selectable Text widget inside a dialog
    err_win = tk.Toplevel()
    err_win.title(title)
    err_win.geometry("600x300")
    err_win.grab_set()
    ttk.Label(err_win, text=title, font=("Segoe UI", 12, "bold")).pack(pady=(12, 4))
    text_widget = tk.Text(err_win, wrap="word", height=10, width=80)
    text_widget.insert("1.0", error_text)
    text_widget.config(state="normal")
    text_widget.pack(padx=12, pady=8, fill="both", expand=True)
    text_widget.focus_set()
    # Add a copy button
    def copy_to_clipboard():
        err_win.clipboard_clear()
        err_win.clipboard_append(error_text)
    ttk.Button(err_win, text="Copy", command=copy_to_clipboard).pack(side="left", padx=12, pady=8)
    ttk.Button(err_win, text="Close", command=err_win.destroy).pack(side="right", padx=12, pady=8)
    return err_win

def start_functions_window(config):
    root = tk.Tk()
    root.title("Edit Functions")
    editor = FunctionsEditor(root, config)
    editor.pack(padx=20, pady=20)
    root.mainloop()

def start_parameters_window(config, schema, selected_groups):
    # Use a hidden root so the second page is a single visible window
    root = tk.Tk()
    root.withdraw()
    ParametersWindow(root, config, schema, selected_groups)
    root.mainloop()

def main():
    if not os.path.exists(CONFIG_PATH):
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"Config file not found: {CONFIG_PATH}")
        return
    config = load_config(CONFIG_PATH)
    start_functions_window(config)

if __name__ == "__main__":
    main()