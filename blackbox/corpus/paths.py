import shutil
from pathlib import Path

from blackbox.config import Settings

INDEX_FILES = ("passages.jsonl", "embeddings.npy", "pid_index.json")


def workspace_data_dir(settings: Settings, workspace: str) -> Path:
    data_dir = Path(settings.DATA_DIR)
    target = data_dir / workspace
    if workspace == "hotpot" and not all((target / name).exists() for name in INDEX_FILES):
        legacy_files = [data_dir / name for name in INDEX_FILES]
        if all(path.exists() for path in legacy_files):
            target.mkdir(parents=True, exist_ok=True)
            for source in legacy_files:
                destination = target / source.name
                if not destination.exists():
                    shutil.copy2(source, destination)
    return target