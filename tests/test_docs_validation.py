from pathlib import Path

from scripts.validate_docs import heading_slugs, unfenced_lines, validate


def write_tree(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_fenced_code_is_ignored():
    lines = unfenced_lines("## Real\n\n```md\n[bad](missing.md)\n## Fake\n```\n")
    assert [line for _, line in lines] == ["## Real", ""]


def test_heading_slugs_preserve_unicode_and_dedupe():
    lines = [(1, "## Síťová diagnostika"), (2, "## Síťová diagnostika")]
    assert heading_slugs(lines) == {"síťová-diagnostika", "síťová-diagnostika-1"}


def test_valid_local_link_image_and_anchor_pass(tmp_path):
    write_tree(
        tmp_path,
        {
            "README.md": "# Home\n\n[Guide](docs/guide.md#prvni-krok)\n![Logo](assets/logo.png)\n",
            "docs/guide.md": "## První krok\n",
            "assets/logo.png": "placeholder",
        },
    )
    assert validate(tmp_path) == []


def test_missing_target_and_anchor_are_reported(tmp_path):
    write_tree(
        tmp_path,
        {"README.md": "[Missing](docs/nope.md#unknown)\n[Bad anchor](#not-here)\n"},
    )
    findings = validate(tmp_path)
    assert len(findings) == 2
    assert any("missing local target" in item.message for item in findings)
    assert any("missing heading" in item.message for item in findings)


def test_code_examples_do_not_create_false_positives(tmp_path):
    write_tree(
        tmp_path,
        {"README.md": "Example:\n\n```markdown\n![placeholder](missing.png)\n```\n"},
    )
    assert validate(tmp_path) == []


def test_links_cannot_escape_repository(tmp_path):
    write_tree(tmp_path, {"README.md": "[outside](../secret.md)\n"})
    findings = validate(tmp_path)
    assert len(findings) == 1
    assert "outside the repository" in findings[0].message
