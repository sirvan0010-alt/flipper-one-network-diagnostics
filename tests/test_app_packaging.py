import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flipctl_app_script_is_valid_python():
    source = (ROOT / "apps" / "network-diagnostics.fap.py").read_text(encoding="utf-8")
    compile(source, "network-diagnostics.fap.py", "exec")


def test_packager_creates_script_and_core_package(tmp_path):
    output = tmp_path / "Network Diagnostics"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "package_flipctl_app.py"),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output / "network-diagnostics.fap.py").is_file()
    assert (output / "flipper_diag" / "store.py").is_file()
    assert (output / "flipper_diag" / "linux_ip.py").is_file()
    assert (output / "README.txt").is_file()

    # Import the copied package with site-packages disabled. This proves that
    # the app bundle contains its own core and does not accidentally rely on the
    # editable checkout or development dependencies installed by CI.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(output)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "import importlib, pkgutil, flipper_diag; "
                "[importlib.import_module(m.name) "
                "for m in pkgutil.iter_modules(flipper_diag.__path__, "
                "'flipper_diag.')]; "
                "print(flipper_diag.__version__)"
            ),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "0.1.0"


def test_packager_refuses_to_overwrite_existing_directory(tmp_path):
    output = tmp_path / "already-there"
    output.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "package_flipctl_app.py"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "output already exists" in result.stderr


def test_packaged_app_launches_with_flipctl_runtime_stub(tmp_path):
    output = tmp_path / "Network Diagnostics"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "package_flipctl_app.py"),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    runtime = tmp_path / "runtime-stub"
    runtime.mkdir()
    (runtime / "flipctl.py").write_text(
        """
from enum import Enum

class Key(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    OK = "ok"
    BACK = "back"
    ESCAPE = "escape"
    VIEW = "view"
    POWER = "power"
    EDIT = "edit"
    RUN = "run"
    PTT = "ptt"

class View:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def on_key(self, handler):
        self.handler = handler
        return handler
    def run(self, *args, **kwargs):
        return None
    def show(self):
        return None
    def redraw(self):
        return None

def Menu(items, **kwargs):
    return View(items=items, **kwargs)

def Detail(rows, **kwargs):
    return View(rows=rows, **kwargs)

def Log(lines, **kwargs):
    return View(lines=lines, **kwargs)

def item(label, **kwargs):
    return {"label": label, **kwargs}

def pair(label, value="", **kwargs):
    return {"label": label, "value": value, **kwargs}

def heading(label, value=""):
    return {"label": label, "value": value}

def rule():
    return {"kind": "rule"}

def text(value, **kwargs):
    return {"value": value, **kwargs}

def wrap(value):
    return [value]
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(runtime)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(output / "network-diagnostics.fap.py"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
