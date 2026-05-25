"""Decode \\uXXXX string literals in a Python source file to UTF-8 Chinese."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def decode_string_literal(match: re.Match[str]) -> str:
    literal = match.group(0)
    try:
        value = ast.literal_eval(literal)
    except (SyntaxError, ValueError):
        return literal
    if not isinstance(value, str):
        return literal
    return repr(value)


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "views/main_window.py")
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(?P<q>["\'])(?:(?!\1).|\\.)*\\u[0-9a-fA-F]{4}(?:(?!\1).|\\.)*\1',
    )
    new_text, count = pattern.subn(decode_string_literal, text)
    target.write_text(new_text, encoding="utf-8")
    print(f"Decoded {count} literals in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
