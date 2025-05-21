import os
import csv
import enum

from utils.time import performance_analyzer

# ======================================================================================================================
def read_csv_file(file_path, meta_lines=1):
    """
    Reads a CSV file and separates metadata (top lines) and data (list of dictionaries).

    :param file_path: Path to the CSV file.
    :param meta_lines: Number of lines at the top of the file considered metadata.
    :return: A dictionary with keys:
             - 'meta': List of strings representing metadata lines.
             - 'data': List of dictionaries representing the rows in the CSV file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        lines = file.readlines()

    meta = lines[:meta_lines]  # Extract metadata lines
    csv_data_lines = lines[meta_lines:]  # Remaining lines are CSV data

    data = []
    if csv_data_lines:
        reader = csv.reader(csv_data_lines)
        headers = next(reader)
        types = next(reader)

        def convert_value(value, dtype):
            if dtype == 'int':
                return int(value)
            elif dtype == 'float':
                return float(value)
            elif dtype == 'bool':
                return value.lower() in ('true', '1', 'yes')
            else:  # default to string
                return value

        for row in reader:
            converted_row = {
                headers[i]: convert_value(row[i], types[i]) for i in range(len(headers))
            }
            data.append(_reconstruct_dict(converted_row))

    return {'meta': meta, 'data': data}

def _reconstruct_dict(flat_dict, sep='.'):
    """
    Reconstructs a nested dictionary from a flattened dictionary.

    :param flat_dict: Flattened dictionary where keys are hierarchical with a separator.
    :param sep: Separator used in the flattened dictionary keys.
    :return: Nested dictionary.
    """
    nested_dict = {}
    for key, value in flat_dict.items():
        keys = key.split(sep)
        d = nested_dict
        for part in keys[:-1]:
            d = d.setdefault(part, {})
        d[keys[-1]] = value
    return nested_dict

# ======================================================================================================================
class CSVLogger:
    def __init__(self):
        """
        Initializes a CSVLogger instance and creates the specified file in the folder.
        If the file already exists, it is deleted and a new one is created.
        :param file: Name of the CSV file.
        :param folder: Directory where the file will be created.
        :param custom_text_header: Text to be added at the top of the CSV file (optional).
        """
        self.file_path = None
        self.file = None
        self.writer = None
        self.fieldnames = None
        self.fieldtypes = None
        self.is_closed = False
        self.index = 0  # Initialize the index column

    def make_file(self, file, folder="./", custom_text_header=None):

        self.index = 0  # Initialize the index column

        self.file_path = os.path.join(folder, file)
        # Ensure the folder exists
        os.makedirs(folder, exist_ok=True)

        # Remove the file if it exists
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

        # Open the file for writing
        self.file = open(self.file_path, mode='w', newline='', encoding='utf-8')

        # Write custom text header if provided
        if custom_text_header:
            if isinstance(custom_text_header, list):
                self.file.write("\n".join(custom_text_header) + "\n")
            else:
                self.file.write(custom_text_header + "\n")

    def write_data(self, data):
        """
        Appends data to the CSV file. The data should be a dictionary or a list of dictionaries.
        Automatically writes the header if this is the first data being written.
        :param data: A dictionary or a list of dictionaries to append to the CSV file.
        """
        if self.is_closed:
            raise RuntimeError("CSVLogger is already closed; cannot log more data.")

        if not isinstance(data, list):
            data = [data]

        # Flatten data to handle nested dictionaries
        flattened_data = [self._flatten_dict(d) for d in data]

        for i, row in enumerate(flattened_data):
            flattened_data[i] = {'index': self.index, **row}
            self.index += 1

        if self.fieldnames is None:
            # Extract fieldnames and fieldtypes from the first dictionary

            self.fieldnames = list(flattened_data[0].keys())
            self.fieldtypes = [self._infer_type(flattened_data[0][key]) for key in
                                         list(flattened_data[0].keys())]


            self.writer = csv.writer(self.file)
            self.writer.writerow(self.fieldnames)
            self.writer.writerow(self.fieldtypes)


        for row in flattened_data:
            self.writer.writerow([row.get(field, '') for field in self.fieldnames])

    def close(self):
        """
        Closes the CSV file.
        """
        if not self.is_closed:
            if self.file:
                self.file.close()
            self.is_closed = True
        self.file = None


    def log_event(self, data):
        """
        Appends a single event's data to the CSV file. A shorthand for append_data.
        :param data: A dictionary representing the event data to log.
        """
        self.write_data(data)

    def _flatten_dict(self, d, parent_key='', sep='.'):
        """
        Recursively flattens a dictionary, adding hierarchical keys with a separator.
        :param d: Dictionary to flatten
        :param parent_key: Key under which current dictionary is nested
        :param sep: Separator for hierarchical keys
        :return: Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, enum.IntEnum):
                items.append((new_key, int(v)))  # Store IntEnum as its int value
            else:
                items.append((new_key, v))
        return dict(items)

    def _infer_type(self, value):
        """
        Infers the type of a value as a string for use in the type header row.
        :param value: The value to infer the type of.
        :return: A string representing the type ('int', 'float', 'bool', 'str').
        """
        if isinstance(value, enum.IntEnum):
            return 'int'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        else:
            return 'str'

    def __del__(self):
        """
        Ensures the CSV file is properly closed when the logger is destroyed.
        """
        self.close()

