# SQLite Viewer Pro

A lightweight, fast SQLite database browser built with Python and Tkinter. Open, browse, search and query any SQLite database without SQL knowledge.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## Features

- **Table Browser** - Automatically lists all tables with sortable data grid
- **Schema View** - Inspect CREATE TABLE statements with syntax highlighting
- **SQL Editor** - Execute custom queries with syntax highlighting and result view
- **Full-Text Search** - Search across all columns in real-time
- **CSV Export** - Export any table or query result to CSV
- **Sorting** - Click column headers to sort ascending/descending
- **Keyboard Shortcuts** - Ctrl+O (open), Ctrl+F (search), Ctrl+E (export), F5 (refresh), F9 (execute SQL)

## Screenshots

### Data Browser
Open any `.db`, `.sqlite`, or `.sqlite3` file and browse tables instantly.

### Schema View
View table definitions with syntax-highlighted CREATE TABLE statements.

### SQL Editor
Write and execute SQL queries with real-time syntax highlighting.

## Installation

### Requirements

- Python 3.10 or higher
- Tkinter (included with most Python installations)

No additional dependencies required - uses only Python standard library.

### Run from Source

```bash
git clone https://github.com/lukisch/SQLiteViewer.git
cd SQLiteViewer
python SQLiteViewer.py
```

### Windows

Double-click `START.bat` or run:

```cmd
python SQLiteViewer.py
```

## Usage

1. **Open a database**: `File > Open Database` or `Ctrl+O`
2. **Browse tables**: Select a table from the dropdown
3. **Search**: Type in the search field to filter rows
4. **View schema**: Switch to the Schema tab
5. **Run SQL**: Switch to the SQL Editor tab, write a query, press `F9`
6. **Export**: `File > Export as CSV` or `Ctrl+E`

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open database |
| `Ctrl+Q` | Quit |
| `Ctrl+E` | Export CSV |
| `Ctrl+F` | Focus search |
| `Ctrl+A` | Select all rows |
| `F5` | Refresh table |
| `F9` | Execute SQL query |

## Comparison

| Feature | SQLite Viewer Pro | DB Browser | DBeaver |
|---------|:-----------------:|:----------:|:-------:|
| Instant startup | Yes | Slow | Slow |
| SQL queries | Yes | Yes | Yes |
| Browse tables | Yes | Yes | Yes |
| Schema view | Yes | Yes | Yes |
| CSV export | Yes | Yes | Yes |
| Full-text search | Yes | Limited | Yes |
| Portable | Yes | Partial | No |
| Lightweight | Yes | No | No |
| No install needed | Yes | No | No |

## Technical Details

- **Framework**: Tkinter + ttk
- **Database**: sqlite3 (stdlib)
- **Dependencies**: None (pure Python stdlib)
- **Single file**: ~750 lines of Python

## License

[MIT](LICENSE)
