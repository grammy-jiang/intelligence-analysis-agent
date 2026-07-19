"""EXIF extraction (design v3 control #11): memory-safe (Pillow, pure-lib, no shell-out), resource-limited
(decompression-bomb cap), never raises on adversarial input. CANDIDATE output only — a proposal, not a fact."""

from __future__ import annotations

import io

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

Image.MAX_IMAGE_PIXELS = (
    64_000_000  # decompression-bomb guard (Pillow raises DecompressionBombError above this)
)


def dms_to_decimal(dms, ref: str) -> float:
    """Convert an EXIF (degrees, minutes, seconds) rational triple to a signed decimal degree."""
    d, m, s = (float(x) for x in dms)
    val = d + m / 60.0 + s / 3600.0
    return -val if ref in ("S", "W") else val


def parse_exif(data: bytes) -> dict[str, str]:
    """Return a flat dict of candidate EXIF fields (+ gps_lat/gps_lon decimals if present). Never raises."""
    out: dict[str, str] = {}
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()  # catch truncated/corrupt before any pixel work
        with Image.open(io.BytesIO(data)) as im:
            getexif = getattr(im, "_getexif", None)
            exif = getexif() if callable(getexif) else None
            if not exif:
                return out
            gps: dict[str, object] = {}
            for tag, val in exif.items():
                name = TAGS.get(tag, str(tag))
                if name == "GPSInfo" and isinstance(val, dict):
                    gps = {GPSTAGS.get(t, str(t)): v for t, v in val.items()}
                elif isinstance(val, (str, int, float)):
                    out[name] = str(val)[:120]
            if gps.get("GPSLatitude") and gps.get("GPSLongitude"):
                try:
                    out["gps_lat"] = str(
                        round(
                            dms_to_decimal(gps["GPSLatitude"], str(gps.get("GPSLatitudeRef", "N"))),
                            6,
                        )
                    )
                    out["gps_lon"] = str(
                        round(
                            dms_to_decimal(
                                gps["GPSLongitude"], str(gps.get("GPSLongitudeRef", "E"))
                            ),
                            6,
                        )
                    )
                except Exception:  # noqa: S110, BLE001 - bad GPS field on adversarial EXIF: skip, never crash
                    pass
    except Exception:  # noqa: S110, BLE001 - adversarial bytes must never crash the parser
        # any parser error (corrupt, bomb, unsupported) → empty candidate set, never a crash on adversarial bytes
        pass
    return out
