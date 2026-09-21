"""Answer-sheet decode, orient, strip and compress. Pure over bytes + limits."""

from __future__ import annotations

import io
from dataclasses import dataclass

from contracts.errors import ValidationFailed

from .constants import PROFILE_DEFAULT, PROFILE_HIGHER_FIDELITY


@dataclass(frozen=True, slots=True)
class CompressResult:
    """One successful compression output."""

    body: bytes
    mime: str
    width: int
    height: int
    sha256: str
    profile_version: str


def _sha256(body: bytes) -> str:
    """Hex digest of body."""
    import hashlib

    return hashlib.sha256(body).hexdigest()


def decode_and_compress(
    source: bytes,
    *,
    max_megapixels: int,
    long_edge_px: int,
    webp_quality: int,
    profile: str = PROFILE_DEFAULT,
) -> CompressResult:
    """Decode JPEG/PNG/WebP, reject animation/bombs, orient, strip, resize, encode.

    Assumes source was already size-checked against max_bytes_per_page.
    Does not handle: HEIC, PDF, multi-page TIFF.
    """
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = max_megapixels * 1_000_000
    try:
        image = Image.open(io.BytesIO(source))
        image.load()
    except Image.DecompressionBombError as exc:
        raise ValidationFailed("files.error.decode_rejected") from exc
    except Exception as exc:
        raise ValidationFailed("files.error.decode_rejected") from exc

    if getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) > 1:
        raise ValidationFailed("files.error.decode_rejected")

    width, height = image.size
    if width < 1 or height < 1:
        raise ValidationFailed("files.error.decode_rejected")
    if (width * height) > (max_megapixels * 1_000_000):
        raise ValidationFailed("files.error.decode_rejected")

    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")

    edge = max(image.size)
    target_edge = long_edge_px
    if profile == PROFILE_HIGHER_FIDELITY:
        target_edge = max(long_edge_px, 3200)
    if edge > target_edge:
        scale = target_edge / float(edge)
        image = image.resize(
            (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))),
            Image.Resampling.LANCZOS,
        )

    # Strip by re-encoding without EXIF.
    out = io.BytesIO()
    use_profile = (
        profile if profile in {PROFILE_DEFAULT, PROFILE_HIGHER_FIDELITY} else PROFILE_DEFAULT
    )
    if use_profile == PROFILE_HIGHER_FIDELITY:
        image.save(out, format="JPEG", quality=95, optimize=True)
        mime = "image/jpeg"
        profile_version = PROFILE_HIGHER_FIDELITY
    else:
        try:
            image.save(out, format="WEBP", quality=webp_quality, method=4)
            mime = "image/webp"
            profile_version = PROFILE_DEFAULT
        except Exception:
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=85, optimize=True)
            mime = "image/jpeg"
            profile_version = PROFILE_DEFAULT
    body = out.getvalue()
    return CompressResult(
        body=body,
        mime=mime,
        width=image.size[0],
        height=image.size[1],
        sha256=_sha256(body),
        profile_version=profile_version,
    )
