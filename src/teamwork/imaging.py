"""Offline image-model capability probe (no network, no prompt leak)."""

from __future__ import annotations

import json
import os
import shutil

IMAGE_MODEL_RANKING = {
    "openai": ("gpt-image-1", "dall-e-3"),
    "google": (
        "imagen-4.0-ultra-generate-001",
        "imagen-4.0-generate-001",
        "gemini-2.5-flash-image",
    ),
    "black-forest-labs": ("flux-1.1-pro", "flux-1-dev", "flux-1-schnell"),
    "stability": ("stable-image-ultra", "sd3.5-large", "sd3.5-medium"),
    "replicate": (
        "black-forest-labs/flux-1.1-pro",
        "stability-ai/stable-diffusion-3.5-large",
    ),
    "local": ("qwen-image-2.1", "sdxl", "sd3.5-large"),
    "ollama-cloud": (),  # text/vision INPUT only as of 2026-10-17
}

IMAGE_PROVIDER_PRIORITY = (
    "openai",
    "google",
    "black-forest-labs",
    "stability",
    "replicate",
    "local",
    "ollama-cloud",
)

IMAGE_PROVIDER_CREDENTIALS = {
    "openai": ("OPENAI_API_KEY",),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "black-forest-labs": ("BFL_API_KEY", "BLACK_FOREST_LABS_API_KEY"),
    "stability": ("STABILITY_API_KEY",),
    "replicate": ("REPLICATE_API_TOKEN",),
    "ollama-cloud": ("OLLAMA_API_KEY",),
}

IMAGE_FALLBACK_HINT = (
    "no cloud image model detected: fall back to a local model, then to a "
    "hand-authored SVG (roles/designer.md, fallback ladder). Do not stall, and "
    "do not report an image that was never generated."
)


def detect_image_provider(env=None) -> str:
    """First provider in priority order that is configured and has a model."""
    env = os.environ if env is None else env
    for provider in IMAGE_PROVIDER_PRIORITY:
        if provider == "local":
            if shutil.which("qimg") or any(key.startswith("QIMG_") for key in env):
                return provider
            continue
        if not IMAGE_MODEL_RANKING.get(provider):
            continue
        if any(env.get(name) for name in IMAGE_PROVIDER_CREDENTIALS.get(provider, ())):
            return provider
    return ""


def resolve_image_model(env=None) -> dict:
    """Decide which image generator to use, without touching the network."""
    env = os.environ if env is None else env
    override = (env.get("TEAMWORK_IMAGE_MODEL") or "").strip()
    if override:
        provider = (env.get("TEAMWORK_IMAGE_PROVIDER") or "custom").strip() or "custom"
        return {
            "provider": provider,
            "model": override,
            "ranked": [],
            "source": "TEAMWORK_IMAGE_MODEL override",
            "fallback": "",
        }
    explicit = (env.get("TEAMWORK_IMAGE_PROVIDER") or "").strip()
    if explicit:
        ranked = list(IMAGE_MODEL_RANKING.get(explicit, ()))
        return {
            "provider": explicit,
            "model": ranked[0] if ranked else "",
            "ranked": ranked,
            "source": "TEAMWORK_IMAGE_PROVIDER",
            "fallback": "" if ranked else IMAGE_FALLBACK_HINT,
        }
    provider = detect_image_provider(env)
    ranked = list(IMAGE_MODEL_RANKING.get(provider, ()))
    return {
        "provider": provider,
        "model": ranked[0] if ranked else "",
        "ranked": ranked,
        "source": "ambient environment" if provider else "none detected",
        "fallback": "" if provider else IMAGE_FALLBACK_HINT,
    }


def cmd_imaging(args) -> int:
    """`teamwork imaging probe` - which image model, if any, is available."""

    decision = resolve_image_model()
    if getattr(args, "json", False):
        print(json.dumps({"command": "imaging.probe", **decision}, indent=2))
        return 0
    print("# imaging probe (offline: environment + PATH only)")
    print(f"  provider:  {decision['provider'] or '-'}")
    print(f"  model:     {decision['model'] or '-'}")
    print(f"  source:    {decision['source']}")
    if decision["ranked"]:
        print("  ranked:    " + " > ".join(decision["ranked"]))
    if decision["model"]:
        print("  supports:  text-to-image, image-to-image")
    else:
        print("  supports:  none")
    if decision["fallback"]:
        print(f"  fallback:  {decision['fallback']}")
    print(
        "  policy:    roles/designer.md (plan, 4+ candidates, visual review,"
        " improvement, privacy and licence red lines)"
    )
    return 0
