import os
import json
from typing import List, Dict, Any

def get_file_extension(file_path: str) -> str:
    """Get the file extension."""
    return os.path.splitext(file_path)[1].lower()

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

def create_document_for_file(file_path: str, root_dir: str) -> Dict[str, Any]:
    """Create a document for indexing."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    relative_path = os.path.relpath(file_path, root_dir)
    
    return {
        "path": relative_path,
        "extension": get_file_extension(file_path),
        "content": content,
    }

def index_codebase(root_dir: str, output_file: str, ignore_dirs: List[str], ignore_files: List[str]) -> None:
    """Index the codebase."""
    files = get_files_to_index(root_dir, ignore_dirs, ignore_files)
    documents = []
    
    for file in files:
        try:
            document = create_document_for_file(file, root_dir)
            documents.append(document)
            print(f"Indexed {document['path']}")
        except Exception as e:
            print(f"Error indexing {file}: {e}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write documents to output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)
    
    print(f"Indexed {len(documents)} files to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index a codebase")
    parser.add_argument("--root-dir", type=str, default=".", help="Root directory of the codebase")
    parser.add_argument("--output-file", type=str, default="index.json", help="Output file")
    parser.add_argument("--ignore-dirs", type=str, nargs="+", default=["node_modules", "venv", "__pycache__", ".git", "dist", "build"], help="Directories to ignore")
    parser.add_argument("--ignore-files", type=str, nargs="+", default=[], help="Files to ignore")
    
    args = parser.parse_args()
    
    index_codebase(args.root_dir, args.output_file, args.ignore_dirs, args.ignore_files) 