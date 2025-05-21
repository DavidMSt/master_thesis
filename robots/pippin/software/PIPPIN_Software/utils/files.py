import inspect
import os
import shutil
from pathlib import Path
import tempfile


# File Path Utilities
def relativeToFullPath(relative_path):
    """
    Resolve the absolute path from a relative path, relative to the caller's module.

    :param relative_path: Relative path to resolve.
    :return: Absolute path.
    """
    # Get the caller's frame
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])

    # Get the caller's directory
    if caller_module and caller_module.__file__:
        caller_dir = Path(caller_module.__file__).parent.resolve()
    else:
        # Fallback to the current working directory if module info is not available
        caller_dir = Path().cwd()

    # Resolve the full path
    full_path = (caller_dir / relative_path).resolve()

    return str(full_path)


def get_script_path(include_file_name=False):
    """
    Get the absolute path of the calling script.

    :param include_file_name: If True, includes the script's file name in the path.
    :return: Absolute path of the calling script or its directory.
    """
    # Get the caller's frame
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])

    if caller_module and caller_module.__file__:
        # Get the absolute path of the script
        script_path = Path(caller_module.__file__).resolve()
        if include_file_name:
            return str(script_path)
        else:
            return str(script_path.parent)
    else:
        # Fallback if the module does not have a __file__ attribute (e.g., interactive session)
        return str(Path.cwd())


def get_script_name(remove_extension=False):
    """
    Get the name of the calling script.

    :param remove_extension: If True, removes the file extension from the script name.
    :return: Name of the calling script.
    """
    # Get the caller's frame
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])

    if caller_module and caller_module.__file__:
        # Get the script's file name
        script_name = Path(caller_module.__file__).name
        if remove_extension:
            return Path(script_name).stem
        else:
            return script_name
    else:
        # Fallback to None if called from an interactive session
        return None


# File Operations
def fileExists(file_path):
    """
    Check if a file exists.

    :param file_path: Path to the file.
    :return: True if file exists, False otherwise.
    """
    return os.path.exists(file_path)


def dirExists(dir_path):
    """
    Check if a directory exists.

    :param dir_path: Path to the directory.
    :return: True if directory exists, False otherwise.
    """
    return os.path.isdir(dir_path)


def makeDir(dir_path):
    """
    Create a directory if it doesn't already exist.

    :param dir_path: Path to the directory.
    """
    if not dirExists(dir_path):
        os.makedirs(dir_path)


def readFile(file_path):
    """
    Read the contents of a file.

    :param file_path: Path to the file.
    :return: Contents of the file as a string.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def writeFile(file_path, content):
    """
    Write content to a file. Creates the file if it doesn't exist.

    :param file_path: Path to the file.
    :param content: Content to write.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)


def appendToFile(file_path, content):
    """
    Append content to a file. Creates the file if it doesn't exist.

    :param file_path: Path to the file.
    :param content: Content to append.
    """
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(content)


def getFileExtension(file_path):
    """
    Get the file extension.

    :param file_path: Path to the file.
    :return: File extension as a string.
    """
    return Path(file_path).suffix


def getFileNameWithoutExtension(file_path):
    """
    Get the file name without its extension.

    :param file_path: Path to the file.
    :return: File name without extension.
    """
    return Path(file_path).stem


def deleteFile(file_path):
    """
    Delete a file if it exists.

    :param file_path: Path to the file.
    """
    if fileExists(file_path):
        os.remove(file_path)


def copyFile(src, dest):
    """
    Copy a file from source to destination.

    :param src: Source file path.
    :param dest: Destination file path.
    """
    shutil.copy2(src, dest)


def moveFile(src, dest):
    """
    Move a file from source to destination.

    :param src: Source file path.
    :param dest: Destination file path.
    """
    shutil.move(src, dest)


def getFileSize(file_path):
    """
    Get the size of a file in bytes.

    :param file_path: Path to the file.
    :return: File size in bytes.
    """
    return os.path.getsize(file_path)


# Directory Operations
def listFilesInDir(dir_path, extension=None):
    """
    List all files in a directory. Optionally filter by extension.

    :param dir_path: Path to the directory.
    :param extension: (Optional) Filter by file extension.
    :return: List of file paths.
    """
    dir_path = Path(dir_path)
    if dirExists(dir_path):
        if extension:
            return [str(file) for file in dir_path.glob(f'*.{extension.lstrip(".")}')]
        return [str(file) for file in dir_path.iterdir() if file.is_file()]
    return []


def isSymlink(path):
    """
    Check if a given path is a symbolic link.

    :param path: Path to check.
    :return: True if the path is a symbolic link, False otherwise.
    """
    return Path(path).is_symlink()


def isDirEmpty(dir_path):
    """
    Check if a directory is empty.

    :param dir_path: Path to the directory.
    :return: True if the directory is empty, False otherwise.
    """
    return len(os.listdir(dir_path)) == 0


def removeDir(dir_path):
    """
    Remove a directory and its contents.

    :param dir_path: Path to the directory.
    """
    if dirExists(dir_path):
        shutil.rmtree(dir_path)


def createTempDir():
    """
    Create a temporary directory.

    :return: Path to the temporary directory.
    """
    return tempfile.mkdtemp()


def joinPaths(*paths):
    """
    Joins multiple path components into a single path.

    Args:
        *paths: Variable number of path components to join.

    Returns:
        str: The resulting joined path.
    """
    return os.path.join(*paths)


def splitExtension(file_path):
    """
    Splits the file path into the root (path without extension) and the extension.

    Args:
        file_path (str): The full file path to split.

    Returns:
        tuple: A tuple (root, extension) where:
            - root: The file path without the extension.
            - extension: The file extension, including the leading dot (e.g., '.txt').
    """
    return os.path.splitext(file_path)


def createFile(file_name: str, extension: str = "") -> str:
    """
    Creates an empty file with the given name and optional extension.

    Args:
        file_name (str): The name of the file (without extension).
        extension (str): The optional extension for the file (e.g., 'txt', 'json').

    Returns:
        str: The full path of the created file.
    """
    # Add the extension to the filename if provided
    if extension:
        file_name = f"{file_name}.{extension.lstrip('.')}"

    try:
        # Create the empty file
        with open(file_name, 'w') as file:
            pass
        return os.path.abspath(file_name)
    except Exception as e:
        print(f"An error occurred while creating the file: {e}")
        raise
