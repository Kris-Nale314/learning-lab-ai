"""
Path Utilities - Consistent file access for Framework Assessment Workbench

This module provides functions for consistent file path handling across the application.
It ensures that paths are resolved correctly regardless of where the code is executed from.
"""

import os
import json
import sys, re
import logging
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

# Configure logging
logger = logging.getLogger("learning-lab-ai.utils.path_utils")

# Get the project root directory
# This assumes the script is in utils/ directory in the project structure
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Define standard directories with consistent naming
DIRS = {
    # Core directories
    "root": PROJECT_ROOT,
    "core": PROJECT_ROOT / "core",
    "utils": PROJECT_ROOT / "utils",
    "pages": PROJECT_ROOT / "pages",
    
    # Data directories
    "data": PROJECT_ROOT / "data",
    "frameworks": PROJECT_ROOT / "data" / "frameworks",
    "outputs": PROJECT_ROOT / "data" / "outputs",
    "samples": PROJECT_ROOT / "data" / "samples",
    "context": PROJECT_ROOT / "data" / "context",
    
    # Logging and temporary files
    "logs": PROJECT_ROOT / "logs",
    "temp": PROJECT_ROOT / "temp",
}

def ensure_dirs() -> None:
    """Ensure all standard directories exist."""
    for dir_name, dir_path in DIRS.items():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {dir_path}")

def get_path(dir_key: str) -> Path:
    """
    Get a path to a standard directory.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'frameworks')
        
    Returns:
        Path object for the directory
    
    Raises:
        ValueError: If the dir_key is not recognized
    """
    if dir_key not in DIRS:
        valid_keys = list(DIRS.keys())
        raise ValueError(f"Unknown directory key: '{dir_key}'. Valid keys: {valid_keys}")
    
    # Ensure the directory exists
    DIRS[dir_key].mkdir(parents=True, exist_ok=True)
    
    return DIRS[dir_key]

def get_file_path(dir_key: str, filename: str) -> Path:
    """
    Get a path to a file in a standard directory.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'frameworks')
        filename: Name of the file
        
    Returns:
        Path object for the file
    """
    return get_path(dir_key) / filename

def list_files(dir_key: str, extension: Optional[str] = None) -> List[Path]:
    """
    List files in a standard directory, optionally filtered by extension.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'frameworks')
        extension: Optional file extension filter (e.g., '.json')
        
    Returns:
        List of Path objects for the files
    """
    dir_path = get_path(dir_key)
    
    if extension:
        # Ensure extension starts with a dot
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        return [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() == extension.lower()]
    else:
        return [f for f in dir_path.iterdir() if f.is_file()]

def save_json(dir_key: str, filename: str, data: Dict[str, Any]) -> Path:
    """
    Save data as JSON to a file in a standard directory.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'frameworks')
        filename: Name of the file
        data: Dictionary to save as JSON
        
    Returns:
        Path object for the saved file
    """
    import json
    
    # Ensure filename has .json extension
    if not filename.lower().endswith('.json'):
        filename = f"{filename}.json"
    
    file_path = get_file_path(dir_key, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved JSON to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {str(e)}")
        raise

def load_json(dir_key: str, filename: str) -> Dict[str, Any]:
    """
    Load JSON data from a file in a standard directory.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'frameworks')
        filename: Name of the file
        
    Returns:
        Dictionary loaded from JSON
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
    """
    import json
    
    # Ensure filename has .json extension
    if not filename.lower().endswith('.json'):
        filename = f"{filename}.json"
    
    file_path = get_file_path(dir_key, filename)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"Loaded JSON from: {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"JSON file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {str(e)}")
        raise

def get_unique_filename(dir_key: str, base_filename: str, extension: str) -> str:
    """
    Get a unique filename in a directory by adding a numbered suffix if needed.
    
    Args:
        dir_key: Key for the directory (e.g., 'data', 'outputs')
        base_filename: Base name for the file (without extension)
        extension: File extension (with or without leading dot)
        
    Returns:
        Unique filename that doesn't exist in the directory
    """
    # Ensure extension starts with a dot
    if not extension.startswith('.'):
        extension = f".{extension}"
    
    dir_path = get_path(dir_key)
    filename = f"{base_filename}{extension}"
    file_path = dir_path / filename
    
    # If file doesn't exist, return the original name
    if not file_path.exists():
        return filename
    
    # Otherwise, add a numbered suffix until a unique name is found
    counter = 1
    while (dir_path / f"{base_filename}_{counter}{extension}").exists():
        counter += 1
    
    return f"{base_filename}_{counter}{extension}"

def save_assessment_result(result: Dict[str, Any], filename_prefix: str = "assessment") -> Path:
    """
    Save assessment result to the outputs directory with a unique filename.
    
    Args:
        result: Assessment result dictionary
        filename_prefix: Prefix for the filename
        
    Returns:
        Path object for the saved file
    """
    import json
    from datetime import datetime
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{filename_prefix}_{timestamp}"
    
    # Get a unique filename
    filename = get_unique_filename("outputs", base_filename, ".json")
    
    # Save the result
    file_path = get_file_path("outputs", filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved assessment result to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving assessment result: {str(e)}")
        raise

def load_framework(filename: str) -> Dict[str, Any]:
    """
    Load a framework from the frameworks directory.
    
    Args:
        filename: Name of the framework file
        
    Returns:
        Framework dictionary
    """
    return load_json("frameworks", filename)

def list_frameworks() -> List[Dict[str, Any]]:
    """
    List all available frameworks.
    
    Returns:
        List of framework dictionaries
    """
    framework_files = list_files("frameworks", ".json")
    frameworks = []
    
    for file_path in framework_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                framework = json.load(f)
                frameworks.append(framework)
        except Exception as e:
            logger.warning(f"Failed to load framework {file_path.name}: {str(e)}")
    
    return frameworks

def save_framework(framework: Dict[str, Any]) -> Path:
    """
    Save a framework to the frameworks directory.
    
    Args:
        framework: Framework dictionary
        
    Returns:
        Path object for the saved file
    """
    # Ensure framework has an ID
    if "id" not in framework:
        raise ValueError("Framework must have an 'id' field")
    
    filename = f"{framework['id']}.json"
    return save_json("frameworks", filename, framework)

def get_project_root() -> Path:
    """
    Get the absolute path to the project root directory.
    
    Returns:
        Path object for the project root directory
    """
    return PROJECT_ROOT

def get_absolute_path(relative_path: Union[str, Path]) -> Path:
    """
    Convert a relative path (from project root) to an absolute path.
    
    Args:
        relative_path: Relative path from project root
        
    Returns:
        Absolute Path object
    """
    return PROJECT_ROOT / Path(relative_path)

# Initialize directories when module is imported
ensure_dirs()