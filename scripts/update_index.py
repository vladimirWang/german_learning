#!/usr/bin/env python3
"""扫描仓库中的 .md 素材，自动生成/更新 grammar.index.md。

每条记录字段：lang / path / tags / level / type / hash
- path：相对于仓库根目录的 posix 路径
- hash：sha256:<64hex>，基于文件内容
- type：从 frontmatter 的 chunk_type 读取，缺省按目录推断（grammar/vocab）
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_NAME = "grammar.index.md"
FRONTMATTER_RE = re.compile(
    r"^<!--\s*\n(.*?)\n-->", re.DOTALL | re.MULTILINE
)


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 HTML 注释形式的 frontmatter。"""
    m = FRONTMATTER_RE.match(text.strip())
    if not m:
        return {}
    data: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def infer_type(path: Path, fm: dict[str, str]) -> str:
    if "chunk_type" in fm and fm["chunk_type"] in {"grammar", "vocab"}:
        return fm["chunk_type"]
    parts = path.parts
    for part in parts:
        if part in {"grammar", "vocab"}:
            return part
    return "grammar"


def collect_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for md in sorted(REPO_ROOT.rglob("*.md")):
        if md.name == INDEX_NAME:
            continue
        rel = md.relative_to(REPO_ROOT).as_posix()
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        # 只收录带 frontmatter 且声明了 lang 的素材文件，跳过 README 等
        if "lang" not in fm:
            continue
        entries.append(
            {
                "lang": fm["lang"],
                "path": rel,
                "tags": fm.get("tags", ""),
                "level": fm.get("level", ""),
                "type": infer_type(md, fm),
                "hash": sha256_file(md),
            }
        )
    return entries


def format_entry(e: dict[str, str]) -> str:
    parts = [
        f"lang:{e['lang']}",
        f"path:{e['path']}",
    ]
    if e["tags"]:
        parts.append(f"tags:{e['tags']}")
    if e["level"]:
        parts.append(f"level:{e['level']}")
    if e["type"]:
        parts.append(f"type:{e['type']}")
    parts.append(f"hash:{e['hash']}")
    return "- " + ", ".join(parts)


def render_index(entries: list[dict[str, str]]) -> str:
    lines = [
        "# 素材索引（grammar.index.md）",
        "",
        "> 由 GitHub Action 自动生成，请勿手工编辑。",
        "> 每条记录：lang / path / tags / level / type / hash",
        "> hash 为文件内容的 sha256，用于增量构建比对。",
        "",
    ]
    for e in entries:
        lines.append(format_entry(e))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    entries = collect_entries()
    new_content = render_index(entries)
    index_path = REPO_ROOT / INDEX_NAME
    old_content = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    if new_content != old_content:
        index_path.write_text(new_content, encoding="utf-8")
        print(f"updated {INDEX_NAME}: {len(entries)} entries")
    else:
        print(f"{INDEX_NAME} up to date: {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
