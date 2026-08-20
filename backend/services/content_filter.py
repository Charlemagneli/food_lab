"""Configurable server-side content filter for community comments."""

import hashlib
import os
import unicodedata
from pathlib import Path


DEFAULT_WORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "blocked_words.txt"
_rules_cache = {}


def _normalize(value):
    """Normalize common spacing and punctuation obfuscation without changing the source."""
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(char for char in normalized if unicodedata.category(char)[0] in {"L", "N"})


def _parse_rule(line, default_category="custom"):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "|" in line:
        category, phrase = (part.strip() for part in line.split("|", 1))
    else:
        category, phrase = default_category, line
    normalized = _normalize(phrase)
    if not category or not normalized:
        return None
    digest = hashlib.sha256(f"{category}|{normalized}".encode("utf-8")).hexdigest()[:16]
    return category, normalized, digest


def _load_rules(path, extra_words):
    path = Path(path)
    try:
        modified = path.stat().st_mtime_ns
    except OSError:
        modified = None
    cache_key = (str(path.resolve()), modified, extra_words)
    if cache_key in _rules_cache:
        return _rules_cache[cache_key]

    lines = []
    try:
        lines.extend(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        pass
    lines.extend(word.strip() for word in str(extra_words or "").split(","))
    rules = tuple(rule for line in lines if (rule := _parse_rule(line)))
    _rules_cache.clear()
    _rules_cache[cache_key] = rules
    return rules


def find_blocked_content(content, config):
    """Return non-sensitive rule metadata when content matches, otherwise ``None``."""
    normalized = _normalize(content)
    if not normalized:
        return None
    words_file = config.get("CONTENT_FILTER_WORDS_FILE") or os.fspath(DEFAULT_WORDS_FILE)
    extra_words = config.get("CONTENT_FILTER_EXTRA_WORDS", "")
    for category, phrase, rule_hash in _load_rules(words_file, extra_words):
        if phrase in normalized:
            return {"category": category, "rule_hash": rule_hash}
    return None
