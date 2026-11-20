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
