from pathlib import Path
import shutil
from utils import sha256

def find_and_copy_uniques(source_dir, existing_dir, output_dir, progress_callback=None):
    """
    Сравнивает файлы в source_dir с existing_dir по sha256.
    Копирует уникальные файлы в output_dir.
    Возвращает количество скопированных файлов и список дубликатов.
    """
    source_dir = Path(source_dir)
    existing_dir = Path(existing_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Хеши существующих файлов
    hash_map = {}
    existing_files = list(existing_dir.iterdir())
    for i, f in enumerate(existing_files):
        if f.is_file():
            hash_map[sha256(f)] = f
        if progress_callback:
            progress_callback(i + 1, len(existing_files))

    # Сравнение новых файлов
    duplicates = []
    copied = 0
    new_files = list(source_dir.iterdir())
    for i, f in enumerate(new_files):
        if not f.is_file():
            continue
        h = sha256(f)
        if h in hash_map:
            duplicates.append((f, hash_map[h]))
        else:
            copied += 1
            shutil.copy2(f, output_dir / f"clean_{copied}{f.suffix}")
        if progress_callback:
            progress_callback(i + 1, len(new_files))

    return copied, duplicates