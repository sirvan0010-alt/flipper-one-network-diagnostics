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
