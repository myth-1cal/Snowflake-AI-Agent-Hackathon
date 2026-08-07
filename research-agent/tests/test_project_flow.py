from pathlib import Path

from project_store import ProjectStore


def test_parse_arxiv_links_supports_multiple_inputs(tmp_path):
    store = ProjectStore(storage_path=tmp_path / "projects.json")

    raw_links = "https://arxiv.org/abs/2401.12345\nabs:2401.67890 2401.11111"

    parsed = store.parse_arxiv_links(raw_links)

    assert parsed == ["2401.12345", "2401.67890", "2401.11111"]
