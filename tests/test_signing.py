from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest

from screenshotscout._serialization import build_canonical_query

# A byte-for-byte copy of the API gateway's signing vectors, shared by every SDK.
_SIGNING_VECTORS = Path(__file__).parent / "fixtures" / "signing-vectors.json"


def _load_signing_vectors() -> list[dict[str, Any]]:
    document: Any = json.loads(_SIGNING_VECTORS.read_text(encoding="utf-8"))
    vectors: list[dict[str, Any]] = document["vectors"]
    return vectors


@pytest.mark.parametrize("vector", _load_signing_vectors(), ids=lambda vector: vector["name"])
def test_signed_text_and_signature_match_the_shared_vectors(vector: dict[str, Any]) -> None:
    pairs = [(name, value) for name, value in vector["params"]]
    signed_text = build_canonical_query(pairs, vector["access_key"])
    signature = hmac.new(
        vector["secret_key"].encode("utf-8"),
        signed_text.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert signed_text == vector["signed_text"]
    assert signature == vector["signature"]
