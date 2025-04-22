"""Shared utilities for indexing and analysis."""
import os
import json
from typing import List, Dict, Any

def load_json_file(file_path: str) -> Any:
    """Load a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(data: Any, file_path: str, indent: int = 2) -> None:
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

def get_file_extension(file_path: str) -> str:
    """Get the extension of a file."""
    return os.path.splitext(file_path)[1].lower()

def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary."""
    text_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", 
        ".txt", ".yml", ".yaml", ".html", ".css", ".scss"
    }
    return get_file_extension(file_path) not in text_extensions

def filter_files(files: List[str], ignore_dirs: List[str], ignore_files: List[str]) -> List[str]:
    """Filter files based on ignore patterns."""
    filtered = []
    for file in files:
        # Check if file is in ignored directory
        if any(ignore_dir in file for ignore_dir in ignore_dirs):
            continue
        # Check if file matches ignored pattern
        if any(file.endswith(ignore_file) for ignore_file in ignore_files):
            continue
        filtered.append(file)
    return filtered

def create_document(
    file_path: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a document from a file."""
    return {
        "path": file_path,
        "content": content,
        "extension": get_file_extension(file_path),
        "metadata": metadata or {},
    } 