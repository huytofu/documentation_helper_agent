# Codebase Indexing Tools

This directory contains tools and scripts for indexing and analyzing the codebase.

## Files

### analyze_shared_state.py
Analyzes shared state patterns in the codebase by:
- Loading indexed files
- Extracting state definitions
- Identifying state usage patterns
- Generating state analysis reports

### index_coagents.py
Specialized indexing script for the coagents codebase that:
- Indexes key paths and files
- Creates structured documents
- Handles coagents-specific file types
- Outputs to coagents_index.json

### coagents_index.json
Contains the indexed data specific to the coagents codebase, including:
- File contents
- File metadata
- Path information
- Language-specific annotations

### index.json
General-purpose index file containing:
- Complete codebase index
- File contents and metadata
- Directory structure
- File relationships

## Usage

### Analyzing Shared State
```bash
python analyze_shared_state.py
```

### Indexing the Codebase
```bash
python index_coagents.py --root-dir .. --output-file coagents_index.json
```

## Notes
- Binary files are excluded from indexing
- Large files may be truncated
- Some file types may be filtered out for performance
- Index files should be regenerated when the codebase changes significantly 