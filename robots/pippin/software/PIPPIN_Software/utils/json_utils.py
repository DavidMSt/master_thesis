import json

import numpy as np


def readJSON(file):
    with open(file) as f:
        data = json.load(f)
    return data


def writeJSON(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=1)


def prepareForSerialization(value):
    if isinstance(value, np.ndarray):
        return value.tolist()  # Convert NumPy arrays to lists
    elif isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()  # Convert NumPy scalars to Python scalars
    elif isinstance(value, dict):
        return {key: prepareForSerialization(val) for key, val in value.items()}  # Recurse for dictionaries
    elif isinstance(value, list):
        return [prepareForSerialization(item) for item in value]  # Recurse for lists
    elif isinstance(value, tuple):
        return tuple(prepareForSerialization(item) for item in value)  # Convert tuple recursively
    else:
        return value  # Return as-is if it's already serializable
