"""Password generation helpers for the webpass client."""

from __future__ import annotations

import secrets
import string

LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"
AMBIGUOUS = set("0O1lI|")


def _resolve_symbols(symbols: bool, allowed_symbols: str | None) -> str | None:
    """Return the symbol charset to use, or None if symbols are disabled."""
    if allowed_symbols is not None:
        if not symbols:
            raise ValueError("allowed_symbols cannot be used when symbols are disabled")
        if allowed_symbols == "":
            raise ValueError("allowed_symbols must not be empty")
        allowed_set = set(SYMBOLS)
        invalid = sorted({ch for ch in allowed_symbols if ch not in allowed_set})
        if invalid:
            raise ValueError(
                f"allowed_symbols contains characters not in SYMBOLS: {''.join(invalid)}"
            )
        # Preserve first-seen order while dropping duplicates.
        return "".join(dict.fromkeys(allowed_symbols))
    if symbols:
        return SYMBOLS
    return None


def generate_password(
    length: int = 24,
    *,
    lowercase: bool = True,
    uppercase: bool = True,
    digits: bool = True,
    symbols: bool = True,
    allowed_symbols: str | None = None,
    exclude_ambiguous: bool = False,
) -> str:
    """Generate a random password from the selected character classes.

    Ensures at least one character from each enabled class is present when
    length is large enough to accommodate them.

    If ``allowed_symbols`` is set, only those symbols (a subset of SYMBOLS)
    are used. It is an error to pass ``allowed_symbols`` when ``symbols`` is False.
    """
    if length < 1:
        raise ValueError("length must be at least 1")

    symbol_charset = _resolve_symbols(symbols, allowed_symbols)

    classes: list[str] = []
    if lowercase:
        classes.append(LOWERCASE)
    if uppercase:
        classes.append(UPPERCASE)
    if digits:
        classes.append(DIGITS)
    if symbol_charset is not None:
        classes.append(symbol_charset)

    if not classes:
        raise ValueError("at least one character class must be enabled")

    if exclude_ambiguous:
        classes = ["".join(ch for ch in charset if ch not in AMBIGUOUS) for charset in classes]
        classes = [charset for charset in classes if charset]
        if not classes:
            raise ValueError("no characters remain after excluding ambiguous characters")

    alphabet = "".join(classes)
    if length < len(classes):
        # Not enough room to guarantee one of each class; sample freely.
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # Guarantee one character from each class, then fill the rest.
    chars = [secrets.choice(charset) for charset in classes]
    chars.extend(secrets.choice(alphabet) for _ in range(length - len(classes)))

    # Shuffle with a CSPRNG so class positions are not predictable.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)
