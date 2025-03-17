import os
import re
from typing import List, Dict, Any
from .utils import load_json_file, save_json_file

def load_indexed_files(index_file: str) -> List[Dict[str, Any]]:
    """Load the indexed files from the index file."""
    return load_json_file(index_file)

def save_analysis_results(results: Dict[str, Any], output_file: str) -> None:
    """Save analysis results to a file."""
    save_json_file(results, output_file) 