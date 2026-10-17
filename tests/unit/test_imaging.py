"""Unit tests for the image-generation capability probe.

The probe decides whether a team may generate a raster asset at all, and which
model is "best quality". It must be deterministic, offline, and honest about
having no model. Policy: the Designer's charter, ``roles/designer.md``.
"""

from __future__ import annotations

import json
import re

import pytest

from teamwork import engine


def no_local_qimg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the machine look like it has no local image CLI."""
    monkeypatch.setattr(engine.shutil, "which", lambda _name: None)


# --------------------------------------------------------------------------- #
# ranking table
# --------------------------------------------------------------------------- #


def test_every_ranked_provider_has_a_detectable_credential():
    for provider, models in engine.IMAGE_MODEL_RANKING.items():
        if provider == "local":
            continue
        if models:
            assert provider in engine.IMAGE_PROVIDER_CREDENTIALS, provider


def test_known_providers_are_ranked_and_ollama_cloud_is_honestly_empty():
    assert engine.IMAGE_MODEL_RANKING["openai"][0] == "gpt-image-1"
    assert engine.IMAGE_MODEL_RANKING["google"][0] == "imagen-4.0-ultra-generate-001"
    assert engine.IMAGE_MODEL_RANKING["local"][0] == "qwen-image-2.1"
    # The provider this project actually runs on must not be reported as capable.
    assert engine.IMAGE_MODEL_RANKING["ollama-cloud"] == ()


def test_provider_priority_is_declared_for_every_ranked_provider():
    for provider in engine.IMAGE_MODEL_RANKING:
        assert provider in engine.IMAGE_PROVIDER_PRIORITY


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #


def test_explicit_model_override_wins(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model(
        {"TEAMWORK_IMAGE_MODEL": "my-flagship", "OPENAI_API_KEY": "x"}
    )
    assert decision["model"] == "my-flagship"
    assert decision["source"] == "TEAMWORK_IMAGE_MODEL override"
    assert decision["fallback"] == ""


def test_explicit_provider_picks_the_top_ranked_model(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({"TEAMWORK_IMAGE_PROVIDER": "google"})
    assert decision["provider"] == "google"
    assert decision["model"] == "imagen-4.0-ultra-generate-001"
    assert decision["ranked"][0] == decision["model"]


def test_ollama_cloud_reports_no_model_and_a_fallback(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({"TEAMWORK_IMAGE_PROVIDER": "ollama-cloud"})
    assert decision["model"] == ""
    assert "local model" in decision["fallback"]


def test_unknown_provider_is_not_assumed_to_be_capable(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({"TEAMWORK_IMAGE_PROVIDER": "acme-images"})
    assert decision["model"] == ""
    assert decision["fallback"]


def test_ambient_credential_selects_that_provider(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({"OPENAI_API_KEY": "present"})
    assert decision["provider"] == "openai"
    assert decision["model"] == "gpt-image-1"


def test_a_provider_without_a_ranked_model_is_skipped(monkeypatch):
    no_local_qimg(monkeypatch)
    # OLLAMA_API_KEY alone must not select ollama-cloud: it has no image model.
    decision = engine.resolve_image_model({"OLLAMA_API_KEY": "present"})
    assert decision["provider"] == ""
    assert decision["model"] == ""


def test_cloud_beats_local_when_both_are_available(monkeypatch):
    monkeypatch.setattr(engine.shutil, "which", lambda _name: "/usr/bin/qimg")
    decision = engine.resolve_image_model({"OPENAI_API_KEY": "present"})
    assert decision["provider"] == "openai"


def test_local_cli_is_detected_when_nothing_else_is(monkeypatch):
    monkeypatch.setattr(engine.shutil, "which", lambda _name: "/usr/bin/qimg")
    decision = engine.resolve_image_model({})
    assert decision["provider"] == "local"
    assert decision["model"] == "qwen-image-2.1"


def test_qimg_env_var_also_detects_local(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({"QIMG_SESSION": "qimg"})
    assert decision["provider"] == "local"


def test_no_model_anywhere_yields_the_fallback_ladder(monkeypatch):
    no_local_qimg(monkeypatch)
    decision = engine.resolve_image_model({})
    assert decision["provider"] == ""
    assert decision["model"] == ""
    assert "SVG" in decision["fallback"]


def test_resolve_reads_the_process_environment_by_default(monkeypatch):
    monkeypatch.setenv("TEAMWORK_IMAGE_MODEL", "from-env")
    decision = engine.resolve_image_model()
    assert decision["model"] == "from-env"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def test_probe_json_is_machine_readable(cli, capsys, monkeypatch):
    no_local_qimg(monkeypatch)
    assert cli("imaging", "probe", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "imaging.probe"
    for key in ("provider", "model", "source", "ranked", "fallback"):
        assert key in payload


def test_probe_exits_zero_without_a_model(cli, capsys, monkeypatch):
    no_local_qimg(monkeypatch)
    assert cli("imaging", "probe") == 0
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "none" in out


def test_probe_requires_a_subcommand(cli):
    # argparse exits 2 for a missing required subcommand; the fixture returns it.
    assert cli("imaging") != 0


# --------------------------------------------------------------------------- #
# the policy ships with the skill bundle
# --------------------------------------------------------------------------- #


def test_imaging_is_folded_into_the_designer_document(repo_root):
    """There is no separate Imaging.md: the Designer owns one document."""
    assert not (repo_root / "references" / "Imaging.md").exists()
    assert not (repo_root / "templates" / "Docs" / "Imaging.md").exists()
    assert not (repo_root / "docs" / "Team" / "Imaging.md").exists()
    assert "Imaging.md" not in engine.DOCS
    assert engine.DOCS["Design.md"] == "Designer"
    # and the Design doc/template carry the visual-asset sections instead
    template = (repo_root / "templates" / "Docs" / "Design.md").read_text(encoding="utf-8")
    for required in ("## Visual assets", "### Assets", "### Review log", "### Improvement log"):
        assert required in template, required


def test_designer_charter_is_the_policy_and_it_is_complete(repo_root):
    text = (repo_root / "roles" / "designer.md").read_text(encoding="utf-8")
    for required in (
        "## Visual assets - own them end to end",
        "imaging probe",
        "Vector first",
        "Improve the winner",
        "iteration log",
        "Never send private data",
        "No real people",
        "Strip metadata",
        "Fallback ladder",
        "Deciding what visual assets the deliverable needs",
    ):
        assert required in text, required
    # "best quality" is prose; it appears capitalised at the start of a sentence.
    assert "best quality" in text.lower()


def test_no_document_still_links_to_a_removed_imaging_file(repo_root):
    """No markdown file may *link* to the removed Imaging.md documents.

    Prose may quote the old path (an append-only decision log does), so this
    checks link targets rather than raw text.
    """
    link = re.compile(r"\]\([^)]*Imaging\.md[^)]*\)")
    for path in list(repo_root.glob("*.md")) + list((repo_root / "docs").rglob("*.md")):
        if ".pi" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not link.search(text), f"{path}: still links to a removed Imaging.md"


def test_skill_entry_point_documents_the_designer_ownership(repo_root):
    text = (repo_root / "SKILL.md").read_text(encoding="utf-8")
    assert "Visual assets are the Designer's call" in text
    assert "roles/designer.md" in text
    assert "Imaging.md" not in text
