import platform


def getOS():
    """
    Detects and returns the operating system of the PC.

    Returns:
        str: 'Windows', 'Mac', or 'Linux'.
    """
    os_name = platform.system()
    if os_name == "Windows":
        return "Windows"
    elif os_name == "Darwin":  # macOS is identified as Darwin
        return "Mac"
    elif os_name == "Linux":
        return "Linux"
    else:
        return "Unknown OS"


# Example usage
if __name__ == "__main__":
    print("Operating System:", getOS())
