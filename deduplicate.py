from pathlib import Path
import shutil
from utils import sha256


def find_duplicates_within_folder(folder, progress_callback=None):
    folder = Path(folder)
    hash_map = {}
    files = list(folder.iterdir())

    for i, f in enumerate(files):
        if f.is_file():
            h = sha256(f)
            if h not in hash_map:
                hash_map[h] = []
            hash_map[h].append(f)
        if progress_callback:
            progress_callback(i + 1, len(files))

    duplicates = []
    for h, files in hash_map.items():
        if len(files) > 1:
            for f in files[1:]:
                duplicates.append((f, files[0]))

    return duplicates


def find_duplicates_across_folders(*folders, progress_callback=None):
    hash_map = {}
    all_files = []
    for folder in folders:
        all_files.extend(list(folder.iterdir()))

    for i, f in enumerate(all_files):
        if f.is_file():
            h = sha256(f)
            if h not in hash_map:
                hash_map[h] = []
            hash_map[h].append(f)
        if progress_callback:
            progress_callback(i + 1, len(all_files))

    duplicates = []
    for h, files in hash_map.items():
        if len(files) > 1:
            for f in files[1:]:
                duplicates.append((f, files[0]))

    return duplicates

