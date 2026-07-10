"""Opaque-token artifact store (design v3 control #12) + magic-byte type check (control #11).

Every stored artifact gets a server-issued UUID token; the token→path map is the only resolver. A caller can
never supply a path — remote-derived names/`../` traversal toward the connector-key store are impossible.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid

_TOKEN_RE = re.compile(r"^art_[0-9a-f]{32}$")

# magic bytes → type; used to verify the REAL type, never the remote Content-Type (control #11).
_MAGIC = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # (WEBP has RIFF....WEBP; RIFF prefix is enough for a candidate)
    (b"%PDF-", "application/pdf"),
]
MAX_ARTIFACT_BYTES = 25 * 1024 * 1024


class ArtifactError(Exception):
    pass


class ArtifactStore:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def put(self, data: bytes) -> str:
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ArtifactError("artifact exceeds size cap")
        token = "art_" + uuid.uuid4().hex
        with open(os.path.join(self.root, token), "wb") as fh:  # filename == token, never remote-derived
            fh.write(data)
        return token

    def _path(self, token: str) -> str:
        if not _TOKEN_RE.match(token):
            raise ArtifactError(f"invalid artifact_ref (not a server-issued token): {token!r}")
        path = os.path.join(self.root, token)
        if not os.path.isfile(path):
            raise ArtifactError(f"unknown artifact_ref: {token}")
        return path

    def read(self, token: str) -> bytes:
        with open(self._path(token), "rb") as fh:
            return fh.read()

    def compute_hash(self, token: str) -> str:
        return hashlib.sha256(self.read(token)).hexdigest()

    def detect_type(self, token: str) -> str | None:
        head = self.read(token)[:16]
        for magic, mime in _MAGIC:
            if head.startswith(magic):
                return mime
        return None
