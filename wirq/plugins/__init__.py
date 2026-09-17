from pathlib import Path

def _list_modules():
    mod_dir = Path(__file__).parent
    return [
        f.stem for f in mod_dir.glob("*.py")
        if f.is_file() and f.name != "__init__.py"
    ]

all_modules = frozenset(sorted(_list_modules()))
