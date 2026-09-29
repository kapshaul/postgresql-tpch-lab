import os

def delete_non_dat_files(directory):
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if not filename.endswith('.dat'):
                file_path = os.path.join(root, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

# Example usage:
directory = "./data/"
delete_non_dat_files(directory)
