#!/usr/bin/env python
"""
Update Index Script

This script updates the indexing for the documentation_helper_agent codebase.
It builds on the existing indexing scripts but ensures it works with the current project structure.
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional

# Determine if a file is binary or not
def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception as e:
        print(f"Error checking if {file_path} is binary: {e}")
        return True

# Get the file extension
def get_file_extension(file_path: str) -> str:
    """Get the file extension."""
    return os.path.splitext(file_path)[1].lower()

# Get the language based on file extension
def get_language_from_extension(file_path: str) -> str:
    """Get the language based on file extension."""
    ext = get_file_extension(file_path)[1:].lower()
    extension_to_language = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
        "jsx": "javascript",
        "json": "json",
        "md": "markdown",
        "html": "html",
        "css": "css",
        "scss": "scss"
    }
    return extension_to_language.get(ext, "text")

# Get the contents of a file
def get_file_contents(file_path: str) -> str:
    """Get the contents of a file."""
    try:
        if is_binary_file(file_path):
            return "[Binary file]"
        
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

# Create a document for indexing
def create_document(file_path: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Create a document for indexing."""
    return {
        "path": file_path,
        "content": content,
        "metadata": metadata
    }

# Create a document for indexing from a file
def create_document_for_indexing(file_path: str, root_dir: str) -> Dict[str, Any]:
    """Create a document for indexing."""
    relative_path = os.path.relpath(file_path, root_dir)
    content = get_file_contents(file_path)
    language = get_language_from_extension(file_path)
    
    return create_document(
        file_path=relative_path,
        content=content,
        metadata={
            "language": language,
            "size": len(content),
            "extension": get_file_extension(file_path)
        }
    )

# Get all files to index
def get_files_to_index(root_dir: str, ignore_dirs: List[str], ignore_files: List[str]) -> List[str]:
    """Get all files to index."""
    all_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            if file not in ignore_files and not file.startswith('.'):
                file_path = os.path.join(root, file)
                all_files.append(file_path)
    
    return all_files

# Save a JSON file
def save_json_file(data: Any, file_path: str) -> None:
    """Save a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {file_path}")
    except Exception as e:
        print(f"Error saving {file_path}: {e}")

# Index the codebase
def index_codebase(root_dir: str, output_file: str, ignore_dirs: List[str], ignore_files: List[str]) -> None:
    """Index the codebase."""
    print(f"Indexing codebase at {root_dir}")
    files = get_files_to_index(root_dir, ignore_dirs, ignore_files)
    print(f"Found {len(files)} files to index")
    
    documents = []
    for i, file in enumerate(files):
        try:
            if i % 50 == 0:
                print(f"Indexed {i}/{len(files)} files...")
            
            document = create_document_for_indexing(file, root_dir)
            documents.append(document)
        except Exception as e:
            print(f"Error indexing {file}: {e}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save documents to output file
    save_json_file(documents, output_file)
    print(f"Indexed {len(documents)} files to {output_file}")

# Main function
def main() -> None:
    parser = argparse.ArgumentParser(description="Index the documentation_helper_agent codebase")
    parser.add_argument("--root-dir", type=str, default="..", help="Root directory of the codebase")
    parser.add_argument("--output-file", type=str, default="coagents_index.json", help="Output file")
    parser.add_argument("--ignore-dirs", type=str, nargs="+", 
                        default=["node_modules", "venv", "__pycache__", ".git", "dist", "build"],
                        help="Directories to ignore")
    parser.add_argument("--ignore-files", type=str, nargs="+", 
                        default=["index.json", "coagents_index.json"],
                        help="Files to ignore")
    
    args = parser.parse_args()
    
    # Ensure root_dir is absolute
    root_dir = os.path.abspath(args.root_dir)
    
    # Ensure output_file is relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, args.output_file)
    
    index_codebase(root_dir, output_file, args.ignore_dirs, args.ignore_files)

if __name__ == "__main__":
    main() 