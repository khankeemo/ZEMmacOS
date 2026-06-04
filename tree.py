import os

# ============================================================
# SIMPLE & SAFE PROJECT TREE PRINTER
# ============================================================

ROOT = os.path.abspath(os.path.dirname(__file__))

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    "env",
    "node_modules",
}

IGNORE_FILES = {
    ".DS_Store",
}

def walk(dir_path, prefix=""):
    try:
        items = sorted(os.listdir(dir_path))
    except (IOError, OSError, PermissionError):
        return

    items = [
        i for i in items
        if i not in IGNORE_DIRS and i not in IGNORE_FILES
    ]

    for index, name in enumerate(items):
        full_path = os.path.join(dir_path, name)
        is_last = index == len(items) - 1

        branch = "└── " if is_last else "├── "
        print(prefix + branch + name)

        if os.path.isdir(full_path):
            extension = "    " if is_last else "│   "
            walk(full_path, prefix + extension)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print(os.path.basename(ROOT) + "/")
    walk(ROOT)
