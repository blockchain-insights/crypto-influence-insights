import os

def save_to_file(content: str, filename: str, directory: str = "./snapshots") -> str:
    """
    Saves the given content to a file and returns the file path.

    Args:
        content (str): The content to be saved.
        filename (str): The name of the file to be created.
        directory (str): The directory where the file will be saved. Defaults to "./snapshots".

    Returns:
        str: The full path to the saved file.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, filename)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    return file_path
