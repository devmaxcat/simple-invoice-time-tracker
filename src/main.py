import os
import sys
from pathlib import Path


def _try_reexec_in_venv() -> bool:
    project_root = Path(__file__).resolve().parents[1]
    venv_python = project_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return False

    try:
        current_python = Path(sys.executable).resolve()
        target_python = venv_python.resolve()
    except OSError:
        return False

    if current_python == target_python:
        return False

    os.execv(str(target_python), [str(target_python), "-m", "src.main", *sys.argv[1:]])
    return True


def main():
    try:
        from src.tui.app import App
    except ModuleNotFoundError as error:
        try:
            _try_reexec_in_venv()
        except OSError:
            pass

        missing_module = error.name or "a required dependency"
        print(
            f"Missing dependency: {missing_module}.\n"
            "Activate your virtual environment and install requirements:\n"
            "  source .venv/bin/activate\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    app = App()
    app.run()


if __name__ == "__main__":
    main()