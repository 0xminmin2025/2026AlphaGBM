"""
Data serialization utilities for converting numpy types to Python native types.
This prevents PostgreSQL schema errors when storing JSON data containing numpy objects.
"""
import numpy as np


def convert_numpy_types(obj):
    """
    Recursively convert numpy data types to Python native types for JSON serialization.
    This prevents PostgreSQL schema errors when storing JSON data.

    Args:
        obj: Any object that may contain numpy types

    Returns:
        Object with all numpy types converted to Python native types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, set):
        return {convert_numpy_types(item) for item in obj}
    else:
        return obj


def safe_json_serialize(data):
    """
    Safely serialize data to JSON-compatible format by converting numpy types.

    Args:
        data: Data structure to serialize

    Returns:
        JSON-serializable data structure
    """
    return convert_numpy_types(data)