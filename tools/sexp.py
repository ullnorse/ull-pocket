"""Minimal S-expression parser/writer for KiCad files.

Atoms: plain str for bare tokens, Q (str subclass) for quoted strings.
"""
import re


class Q(str):
    """Quoted string atom."""


_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"parse error at {pos}: {text[pos:pos+40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            lst = stack.pop()
            stack[-1].append(lst)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return "(" + " ".join(_atom(c) for c in node) + ")"
    out = "(" + " ".join(_atom(c) for c in node if not isinstance(c, list))
    # keep leading atoms on the first line, then children
    parts = []
    for c in node:
        if isinstance(c, list):
            parts.append("\n" + "\t" * (indent + 1) + dump(c, indent + 1))
    # handle atoms that appear after lists (rare) by appending inline
    return out + "".join(parts) + "\n" + "\t" * indent + ")"


def find(node, key):
    """Return first child list whose head == key."""
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def findall(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def walk(node):
    yield node
    for c in node:
        if isinstance(c, list):
            yield from walk(c)
