#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Viewer - Vollständiger Datenbank-Browser
================================================

Features:
- Datenbank öffnen und durchsuchen
- Schema-Ansicht (CREATE TABLE Statements)
- CSV/Excel Export
- Volltext-Suche
- SQL-Editor mit Ausführung
- Sortierung und Filterung
"""

import os
import re
import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from typing import Optional, List, Tuple, Any

APP_TITLE = "SQLite Viewer Pro"
APP_VERSION = "2.0.0"
DEFAULT_LIMIT = 1000


class SqlViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # State
        self.conn: sqlite3.Connection | None = None
        self.db_path: str | None = None
        self.current_columns: List[str] = []
        self.current_data: List[Tuple] = []
        self.sort_column: str | None = None
        self.sort_reverse: bool = False

        # UI
        self._build_menu()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        # Styling
        self._setup_styles()

    def _setup_styles(self):
        """Konfiguriere ttk Styles."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=('Segoe UI', 9, 'bold'))

    # ==================== MENU ====================
    def _build_menu(self):
        menubar = tk.Menu(self)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Datenbank öffnen…", command=self.open_db, accelerator="Ctrl+O")
        file_menu.add_command(label="Datenbank schließen", command=self.close_db)
        file_menu.add_separator()
        file_menu.add_command(label="Als CSV exportieren…", command=self.export_csv, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.destroy, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Datei", menu=file_menu)

        # Bearbeiten-Menü
        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Suchen…", command=self._focus_search, accelerator="Ctrl+F")
        edit_menu.add_command(label="Alle auswählen", command=self._select_all, accelerator="Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(label="Refresh", command=self.load_selected_table, accelerator="F5")
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)

        # Ansicht-Menü
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="Daten-Tab", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="Schema-Tab", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="SQL-Editor", command=lambda: self.notebook.select(2))
        menubar.add_cascade(label="Ansicht", menu=view_menu)

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Über…", command=self._show_about)
        menubar.add_cascade(label="Hilfe", menu=help_menu)

        self.config(menu=menubar)

        # Shortcuts
        self.bind_all("<Control-o>", lambda e: self.open_db())
        self.bind_all("<Control-q>", lambda e: self.destroy())
        self.bind_all("<Control-e>", lambda e: self.export_csv())
        self.bind_all("<Control-f>", lambda e: self._focus_search())
        self.bind_all("<Control-a>", lambda e: self._select_all())
        self.bind_all("<F5>", lambda e: self.load_selected_table())

    # ==================== TOOLBAR ====================
    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(side=tk.TOP, fill=tk.X)

        # DB-Pfad
        self.db_label = ttk.Label(bar, text="DB: –", width=40, anchor="w")
        self.db_label.pack(side=tk.LEFT, padx=(0, 10))

        # Tabellen-Auswahl
        ttk.Label(bar, text="Tabelle:").pack(side=tk.LEFT)
        self.table_var = tk.StringVar()
        self.table_combo = ttk.Combobox(bar, textvariable=self.table_var, state="readonly", width=25)
        self.table_combo.pack(side=tk.LEFT, padx=6)
        self.table_combo.bind("<<ComboboxSelected>>", lambda e: self.load_selected_table())

        # Limit
        ttk.Label(bar, text="Limit:").pack(side=tk.LEFT, padx=(10, 0))
        self.limit_var = tk.IntVar(value=DEFAULT_LIMIT)
        self.limit_entry = ttk.Spinbox(bar, from_=1, to=1_000_000, increment=100,
                                        textvariable=self.limit_var, width=8)
        self.limit_entry.pack(side=tk.LEFT, padx=6)

        # Suchfeld
        ttk.Label(bar, text="🔍").pack(side=tk.LEFT, padx=(15, 0))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=4)
        self.search_entry.bind("<Return>", lambda e: self._search_data())
        self.search_entry.bind("<KeyRelease>", lambda e: self._search_data())

        # Buttons
        ttk.Button(bar, text="⟳ Refresh", command=self.load_selected_table, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="📋 Export", command=self.export_csv, width=10).pack(side=tk.LEFT, padx=4)

    # ==================== NOTEBOOK (Tabs) ====================
    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Daten
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="📊 Daten")
        self._build_data_tab()

        # Tab 2: Schema
        self.schema_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.schema_frame, text="🔧 Schema")
        self._build_schema_tab()

        # Tab 3: SQL-Editor
        self.sql_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sql_frame, text="💻 SQL-Editor")
        self._build_sql_tab()

    def _build_data_tab(self):
        """Daten-Tab mit Treeview."""
        container = ttk.Frame(self.data_frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Treeview
        self.tree = ttk.Treeview(container, show="headings", selectmode="extended")
        self.tree["columns"] = ()

        # Scrollbars
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Sortierung bei Klick auf Header
        self.tree.bind("<Button-1>", self._on_header_click)

    def _build_schema_tab(self):
        """Schema-Tab mit CREATE TABLE Statements."""
        # Toolbar
        toolbar = ttk.Frame(self.schema_frame, padding=5)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Tabelle:").pack(side=tk.LEFT)
        self.schema_table_var = tk.StringVar()
        self.schema_combo = ttk.Combobox(toolbar, textvariable=self.schema_table_var,
                                          state="readonly", width=30)
        self.schema_combo.pack(side=tk.LEFT, padx=6)
        self.schema_combo.bind("<<ComboboxSelected>>", lambda e: self._load_schema())

        ttk.Button(toolbar, text="Alle Schemas anzeigen", command=self._load_all_schemas).pack(side=tk.LEFT, padx=10)

        # Text-Widget für Schema
        text_frame = ttk.Frame(self.schema_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.schema_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10),
                                    bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        schema_vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.schema_text.yview)
        schema_hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.schema_text.xview)
        self.schema_text.configure(yscrollcommand=schema_vsb.set, xscrollcommand=schema_hsb.set)

        self.schema_text.grid(row=0, column=0, sticky="nsew")
        schema_vsb.grid(row=0, column=1, sticky="ns")
        schema_hsb.grid(row=1, column=0, sticky="ew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Syntax Highlighting Tags
        self.schema_text.tag_configure("keyword", foreground="#569cd6")
        self.schema_text.tag_configure("type", foreground="#4ec9b0")
        self.schema_text.tag_configure("string", foreground="#ce9178")
        self.schema_text.tag_configure("comment", foreground="#6a9955")

    def _build_sql_tab(self):
        """SQL-Editor Tab."""
        # Splitter
        paned = ttk.PanedWindow(self.sql_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # SQL-Eingabe
        input_frame = ttk.LabelFrame(paned, text="SQL-Query", padding=5)
        paned.add(input_frame, weight=1)

        self.sql_text = tk.Text(input_frame, wrap=tk.NONE, font=("Consolas", 11),
                                 bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", height=8)
        sql_vsb = ttk.Scrollbar(input_frame, orient="vertical", command=self.sql_text.yview)
        self.sql_text.configure(yscrollcommand=sql_vsb.set)

        self.sql_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sql_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # SQL Tags
        self.sql_text.tag_configure("keyword", foreground="#569cd6")
        self.sql_text.bind("<KeyRelease>", self._highlight_sql)

        # Buttons
        btn_frame = ttk.Frame(self.sql_frame, padding=5)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="▶ Ausführen (F9)", command=self.execute_sql).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Leeren", command=lambda: self.sql_text.delete("1.0", tk.END)).pack(side=tk.LEFT)
        self.sql_status = ttk.Label(btn_frame, text="")
        self.sql_status.pack(side=tk.RIGHT, padx=10)

        self.bind_all("<F9>", lambda e: self.execute_sql())

        # Ergebnis
        result_frame = ttk.LabelFrame(paned, text="Ergebnis", padding=5)
        paned.add(result_frame, weight=2)

        self.sql_result_tree = ttk.Treeview(result_frame, show="headings")
        result_vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.sql_result_tree.yview)
        result_hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.sql_result_tree.xview)
        self.sql_result_tree.configure(yscrollcommand=result_vsb.set, xscrollcommand=result_hsb.set)

        self.sql_result_tree.grid(row=0, column=0, sticky="nsew")
        result_vsb.grid(row=0, column=1, sticky="ns")
        result_hsb.grid(row=1, column=0, sticky="ew")
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

    def _build_statusbar(self):
        """Status-Leiste unten."""
        self.statusbar = ttk.Frame(self, padding=(5, 2))
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="Bereit")
        ttk.Label(self.statusbar, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.row_count_var = tk.StringVar(value="")
        ttk.Label(self.statusbar, textvariable=self.row_count_var, anchor="e").pack(side=tk.RIGHT)

    # ==================== DATABASE OPERATIONS ====================
    def open_db(self):
        path = filedialog.askopenfilename(
            title="SQLite-Datenbank öffnen",
            filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("Alle Dateien", "*.*")]
        )
        if not path:
            return

        self.close_db()

        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            self.conn = conn
            self.db_path = path
            self.db_label.config(text=f"DB: {os.path.basename(path)}")
            self._set_status(f"Verbunden: {path}")
            self._load_tables()
        except Exception as e:
            messagebox.showerror("Fehler beim Öffnen", str(e))
            self._set_status("Fehler")

    def close_db(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            self.db_path = None
            self.db_label.config(text="DB: –")
            self._clear_tree()
            self.table_combo["values"] = []
            self.schema_combo["values"] = []
            self._set_status("Datenbank geschlossen")

    def _load_tables(self):
        if not self.conn:
            return
        try:
            cur = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [r[0] for r in cur.fetchall()]
            self.table_combo["values"] = tables
            self.schema_combo["values"] = tables

            if tables:
                self.table_combo.current(0)
                self.schema_combo.current(0)
                self.load_selected_table()
                self._load_schema()
            else:
                self.table_combo.set("")
                self._clear_tree()
                self._set_status("Keine Tabellen gefunden")
        except Exception as e:
            messagebox.showerror("Fehler", f"Tabellen konnten nicht geladen werden:\n{e}")

    def load_selected_table(self):
        table = self.table_var.get()
        if not table or not self.conn:
            return

        limit = max(1, int(self.limit_var.get() or DEFAULT_LIMIT))

        try:
            # Spalten bestimmen
            cur = self.conn.execute(f"PRAGMA table_info({self._ident(table)})")
            cols = [row[1] for row in cur.fetchall()]
            if not cols:
                self._clear_tree()
                self._set_status("Tabelle hat keine Spalten")
                return

            self.current_columns = cols

            # Sortierung
            order_clause = ""
            if self.sort_column and self.sort_column in cols:
                direction = "DESC" if self.sort_reverse else "ASC"
                order_clause = f" ORDER BY {self._ident(self.sort_column)} {direction}"

            # Daten holen
            query = f"SELECT * FROM {self._ident(table)}{order_clause} LIMIT ?"
            cur = self.conn.execute(query, (limit,))
            rows = cur.fetchall()
            self.current_data = [tuple(row) for row in rows]

            self._populate_tree(cols, rows)

            # Zähle Gesamtzeilen
            count_cur = self.conn.execute(f"SELECT COUNT(*) FROM {self._ident(table)}")
            total = count_cur.fetchone()[0]

            self._set_status(f"Tabelle: {table}")
            self.row_count_var.set(f"Zeilen: {len(rows)} / {total}")

        except Exception as e:
            messagebox.showerror("Fehler beim Laden", str(e))

    # ==================== SCHEMA ====================
    def _load_schema(self):
        table = self.schema_table_var.get()
        if not table or not self.conn:
            return

        try:
            cur = self.conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            result = cur.fetchone()
            if result and result[0]:
                self.schema_text.config(state=tk.NORMAL)
                self.schema_text.delete("1.0", tk.END)
                self.schema_text.insert("1.0", result[0])
                self._highlight_schema()
                self.schema_text.config(state=tk.DISABLED)

                # Zusätzliche Infos
                info = self._get_table_info(table)
                self.schema_text.config(state=tk.NORMAL)
                self.schema_text.insert(tk.END, f"\n\n-- Tabellen-Info --\n{info}")
                self.schema_text.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _load_all_schemas(self):
        if not self.conn:
            return

        try:
            cur = self.conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            schemas = cur.fetchall()

            self.schema_text.config(state=tk.NORMAL)
            self.schema_text.delete("1.0", tk.END)

            for name, sql in schemas:
                if sql:
                    self.schema_text.insert(tk.END, f"-- {name} --\n{sql};\n\n")

            self._highlight_schema()
            self.schema_text.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _get_table_info(self, table: str) -> str:
        """Holt zusätzliche Tabelleninformationen."""
        info_parts = []

        try:
            # Spalteninfo
            cur = self.conn.execute(f"PRAGMA table_info({self._ident(table)})")
            columns = cur.fetchall()
            info_parts.append(f"Spalten: {len(columns)}")

            # Zeilenanzahl
            cur = self.conn.execute(f"SELECT COUNT(*) FROM {self._ident(table)}")
            count = cur.fetchone()[0]
            info_parts.append(f"Zeilen: {count}")

            # Indizes
            cur = self.conn.execute(f"PRAGMA index_list({self._ident(table)})")
            indexes = cur.fetchall()
            if indexes:
                info_parts.append(f"Indizes: {len(indexes)}")

            # Foreign Keys
            cur = self.conn.execute(f"PRAGMA foreign_key_list({self._ident(table)})")
            fks = cur.fetchall()
            if fks:
                info_parts.append(f"Foreign Keys: {len(fks)}")

        except Exception:
            pass

        return "\n".join(info_parts)

    def _highlight_schema(self):
        """Syntax-Highlighting für Schema."""
        keywords = ["CREATE", "TABLE", "PRIMARY", "KEY", "NOT", "NULL", "UNIQUE",
                    "DEFAULT", "FOREIGN", "REFERENCES", "INDEX", "ON", "IF", "EXISTS",
                    "AUTOINCREMENT", "CHECK", "CONSTRAINT"]
        types = ["INTEGER", "TEXT", "REAL", "BLOB", "VARCHAR", "CHAR", "BOOLEAN",
                 "DATE", "DATETIME", "TIMESTAMP", "NUMERIC", "FLOAT", "DOUBLE"]

        content = self.schema_text.get("1.0", tk.END)

        for keyword in keywords:
            self._highlight_word(self.schema_text, keyword, "keyword")

        for dtype in types:
            self._highlight_word(self.schema_text, dtype, "type")

    def _highlight_word(self, widget, word, tag):
        """Hebt ein Wort im Text-Widget hervor."""
        start = "1.0"
        while True:
            pos = widget.search(r'\m' + word + r'\M', start, tk.END, regexp=True, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(word)}c"
            widget.tag_add(tag, pos, end)
            start = end

    # ==================== SQL EDITOR ====================
    def execute_sql(self):
        if not self.conn:
            messagebox.showwarning("Warnung", "Keine Datenbank geöffnet.")
            return

        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            return

        try:
            start_time = datetime.now()
            cur = self.conn.execute(sql)

            # Prüfe ob SELECT-Statement
            if sql.upper().strip().startswith("SELECT"):
                rows = cur.fetchall()
                if rows:
                    cols = [desc[0] for desc in cur.description]
                    self._populate_sql_result(cols, rows)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    self.sql_status.config(text=f"✓ {len(rows)} Zeilen in {elapsed:.3f}s")
                else:
                    self._clear_sql_result()
                    self.sql_status.config(text="✓ Keine Ergebnisse")
            else:
                self.conn.commit()
                affected = cur.rowcount
                self._clear_sql_result()
                self.sql_status.config(text=f"✓ {affected} Zeilen betroffen")
                self._load_tables()  # Aktualisiere Tabellenliste

        except Exception as e:
            self.sql_status.config(text=f"✗ Fehler")
            messagebox.showerror("SQL-Fehler", str(e))

    def _populate_sql_result(self, columns: List[str], rows: List[Tuple]):
        """Füllt das SQL-Ergebnis-Treeview."""
        self.sql_result_tree.delete(*self.sql_result_tree.get_children())
        self.sql_result_tree["columns"] = columns

        for c in columns:
            self.sql_result_tree.heading(c, text=c)
            self.sql_result_tree.column(c, width=120, anchor="w")

        for row in rows:
            values = [self._format_value(v) for v in row]
            self.sql_result_tree.insert("", tk.END, values=values)

    def _clear_sql_result(self):
        self.sql_result_tree.delete(*self.sql_result_tree.get_children())
        self.sql_result_tree["columns"] = ()

    def _highlight_sql(self, event=None):
        """Einfaches SQL-Highlighting."""
        keywords = ["SELECT", "FROM", "WHERE", "AND", "OR", "INSERT", "UPDATE",
                    "DELETE", "CREATE", "DROP", "ALTER", "TABLE", "INTO", "VALUES",
                    "SET", "ORDER", "BY", "GROUP", "HAVING", "JOIN", "LEFT", "RIGHT",
                    "INNER", "OUTER", "ON", "AS", "DISTINCT", "LIMIT", "OFFSET",
                    "UNION", "EXCEPT", "INTERSECT", "NULL", "NOT", "IN", "LIKE",
                    "BETWEEN", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END"]

        # Entferne alte Tags
        self.sql_text.tag_remove("keyword", "1.0", tk.END)

        for keyword in keywords:
            self._highlight_word(self.sql_text, keyword, "keyword")

    # ==================== EXPORT ====================
    def export_csv(self):
        if not self.current_columns or not self.current_data:
            messagebox.showwarning("Export", "Keine Daten zum Exportieren.")
            return

        table = self.table_var.get() or "export"
        default_name = f"{table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        path = filedialog.asksaveasfilename(
            title="Als CSV exportieren",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )

        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                writer.writerow(self.current_columns)
                writer.writerows(self.current_data)

            self._set_status(f"Exportiert: {os.path.basename(path)}")
            messagebox.showinfo("Export", f"Erfolgreich exportiert:\n{path}\n\n{len(self.current_data)} Zeilen")

        except Exception as e:
            messagebox.showerror("Export-Fehler", str(e))

    # ==================== SEARCH ====================
    def _search_data(self):
        """Filtert die Daten basierend auf dem Suchbegriff."""
        search_term = self.search_var.get().strip().lower()

        if not search_term:
            # Zeige alle Daten
            self.load_selected_table()
            return

        if not self.current_columns or not self.conn:
            return

        table = self.table_var.get()
        if not table:
            return

        # Suche in allen Spalten
        try:
            conditions = " OR ".join([f"{self._ident(col)} LIKE ?" for col in self.current_columns])
            query = f"SELECT * FROM {self._ident(table)} WHERE {conditions} LIMIT ?"
            params = [f"%{search_term}%" for _ in self.current_columns]
            params.append(self.limit_var.get())

            cur = self.conn.execute(query, params)
            rows = cur.fetchall()

            self._clear_tree()
            self.tree["columns"] = self.current_columns
            for c in self.current_columns:
                self.tree.heading(c, text=c, command=lambda col=c: self._sort_by_column(col))
                self.tree.column(c, width=120, anchor="w")

            for row in rows:
                values = [self._format_value(row[c]) for c in self.current_columns]
                self.tree.insert("", tk.END, values=values)

            self.row_count_var.set(f"Gefunden: {len(rows)}")

        except Exception as e:
            self._set_status(f"Suchfehler: {e}")

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    # ==================== SORTING ====================
    def _on_header_click(self, event):
        """Handler für Klicks auf Spalten-Header."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.tree.identify_column(event.x)
            col_idx = int(column.replace("#", "")) - 1
            if 0 <= col_idx < len(self.current_columns):
                self._sort_by_column(self.current_columns[col_idx])

    def _sort_by_column(self, column: str):
        """Sortiert die Tabelle nach einer Spalte."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        self.load_selected_table()

    # ==================== TREE HELPERS ====================
    def _clear_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ()

    def _populate_tree(self, columns: List[str], rows: List):
        self._clear_tree()

        self.tree["columns"] = columns
        for c in columns:
            # Sortierindikator
            indicator = ""
            if c == self.sort_column:
                indicator = " ↓" if self.sort_reverse else " ↑"

            self.tree.heading(c, text=c + indicator, command=lambda col=c: self._sort_by_column(col))
            self.tree.column(c, width=120, anchor="w")

        for row in rows:
            if isinstance(row, sqlite3.Row):
                values = [self._format_value(row[c]) for c in columns]
            else:
                values = [self._format_value(v) for v in row]
            self.tree.insert("", tk.END, values=values)

    def _format_value(self, value: Any) -> str:
        """Formatiert einen Wert für die Anzeige."""
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            return f"[BLOB {len(value)} bytes]"
        return str(value)

    def _select_all(self):
        """Wählt alle Zeilen im Treeview aus."""
        self.tree.selection_set(self.tree.get_children())

    # ==================== UTILS ====================
    _SQLITE_KEYWORDS = {
        "ABORT", "ACTION", "ADD", "AFTER", "ALL", "ALTER", "ANALYZE", "AND",
        "AS", "ASC", "ATTACH", "AUTOINCREMENT", "BEFORE", "BEGIN", "BETWEEN",
        "BY", "CASCADE", "CASE", "CAST", "CHECK", "COLLATE", "COLUMN",
        "COMMIT", "CONFLICT", "CONSTRAINT", "CREATE", "CROSS", "CURRENT_DATE",
        "CURRENT_TIME", "CURRENT_TIMESTAMP", "DATABASE", "DEFAULT", "DEFERRABLE",
        "DEFERRED", "DELETE", "DESC", "DETACH", "DISTINCT", "DROP", "EACH",
        "ELSE", "END", "ESCAPE", "EXCEPT", "EXCLUSIVE", "EXISTS", "EXPLAIN",
        "FAIL", "FOR", "FOREIGN", "FROM", "FULL", "GLOB", "GROUP", "HAVING",
        "IF", "IGNORE", "IMMEDIATE", "IN", "INDEX", "INDEXED", "INITIALLY",
        "INNER", "INSERT", "INSTEAD", "INTERSECT", "INTO", "IS", "ISNULL",
        "JOIN", "KEY", "LEFT", "LIKE", "LIMIT", "MATCH", "NATURAL", "NO",
        "NOT", "NOTNULL", "NULL", "OF", "OFFSET", "ON", "OR", "ORDER", "OUTER",
        "PLAN", "PRAGMA", "PRIMARY", "QUERY", "RAISE", "RECURSIVE", "REFERENCES",
        "REGEXP", "REINDEX", "RELEASE", "RENAME", "REPLACE", "RESTRICT",
        "RIGHT", "ROLLBACK", "ROW", "SAVEPOINT", "SELECT", "SET", "TABLE",
        "TEMP", "TEMPORARY", "THEN", "TO", "TRANSACTION", "TRIGGER", "UNION",
        "UNIQUE", "UPDATE", "USING", "VACUUM", "VALUES", "VIEW", "VIRTUAL",
        "WHEN", "WHERE", "WITH", "WITHOUT"
    }

    def _ident(self, name: str) -> str:
        """Gibt einen sicheren SQLite-Identifier zurück."""
        if not name:
            raise ValueError("Identifier darf nicht leer sein.")

        is_simple = re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None
        is_keyword = name.upper() in self._SQLITE_KEYWORDS

        if not is_simple or is_keyword:
            safe_name = name.replace('"', '""')
            return f'"{safe_name}"'

        return name

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _show_about(self):
        messagebox.showinfo(
            "Über SQLite Viewer",
            f"{APP_TITLE}\nVersion {APP_VERSION}\n\n"
            "Features:\n"
            "• Datenbank durchsuchen\n"
            "• Schema-Ansicht\n"
            "• SQL-Editor\n"
            "• CSV-Export\n"
            "• Volltext-Suche\n"
            "• Sortierung\n\n"
            "© 2026 lukisch"
        )


if __name__ == "__main__":
    app = SqlViewer()
    app.mainloop()
