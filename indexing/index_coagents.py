import os
import json
import argparse
from typing import List, Dict, Any, Optional
from .utils import (
    load_json_file, 
    save_json_file, 
    get_file_extension, 
    is_binary_file,
    create_document
)

def get_file_contents(file_path: str) -> str:
    """Get the contents of a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

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
            "size": len(content)
        }
    ) 