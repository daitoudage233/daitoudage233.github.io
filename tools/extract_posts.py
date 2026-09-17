#!/usr/bin/env python3
"""把 daitoudage233.github.io 里已经发布的文章提取成 Markdown。

这个仓库是 `hexo generate` 的产物：只有生成的 HTML，没有 Hexo 源码。所以这里把每篇文章
的正文从 HTML 反向取出来，整理成可直接编辑的 Markdown：

    posts/<年>/<年-月-日>-<slug>.md   正文 + front matter（标题 / 时间 / 标签 / 原站链接）
    posts/INDEX.md                    全部文章清单

仓库里已发布的站点本身（各个 index.html）不会被改动，线上地址照旧。

用法（在仓库根目录）：
    python3 tools/extract_posts.py            # 生成或刷新 posts/
    python3 tools/extract_posts.py --check    # 只统计和报告，不写文件
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys
from urllib.parse import unquote
from html.parser import HTMLParser

SITE = "https://daitoudage233.github.io"
BACKSLASH = chr(92)
VOID_TAGS = {"br", "hr", "img", "meta", "link", "input", "source", "col"}
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
BLOCK_TAGS = set(HEADINGS) | {
    "p", "div", "section", "article", "ul", "ol", "li", "blockquote",
    "pre", "hr", "table", "figure", "figcaption",
}


# --------------------------------------------------------------------------- #
# 一棵够用的 HTML 树
# --------------------------------------------------------------------------- #
class Node:
    __slots__ = ("tag", "attrs", "text", "children")

    def __init__(self, tag=None, attrs=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.text = text
        self.children = []

    def classes(self):
        return (self.attrs.get("class") or "").split()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(Node(text=data))


def find_all(node, tag=None, cls=None):
    out = []
    for child in node.children:
        if child.tag and (tag is None or child.tag == tag) and (cls is None or cls in child.classes()):
            out.append(child)
        out.extend(find_all(child, tag, cls))
    return out


def find_one(node, tag=None, cls=None):
    hits = find_all(node, tag, cls)
    return hits[0] if hits else None


def plain(node):
    """节点里的纯文本，用来取标题、标签名这类短文本。"""
    if node is None:
        return ""
    if node.text is not None:
        return node.text
    return "".join(plain(child) for child in node.children)


# --------------------------------------------------------------------------- #
# HTML -> Markdown
# --------------------------------------------------------------------------- #
def squeeze(text):
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t\r\n]+", " ", text)
    return text


def inline(node):
    """把节点渲染成行内 Markdown，节点本身是行内元素（img、a、strong…）时也一并渲染。"""
    if node.text is not None:
        return squeeze(node.text)
    tag, cls = node.tag, node.classes()
    if "headerlink" in cls or "post-anchor" in cls:
        return ""
    if node.attrs.get("id") == "more":
        return ""
    if tag == "img":
        return "![" + node.attrs.get("alt", "") + "](" + node.attrs.get("src", "") + ")"
    if tag == "br":
        return "  \n"
    if tag == "code":
        return "`" + squeeze(plain(node)).strip() + "`"
    body = "".join(inline(child) for child in node.children)
    if tag in ("strong", "b"):
        return "**" + body.strip() + "**"
    if tag in ("em", "i"):
        return "*" + body.strip() + "*"
    if tag in ("del", "s", "strike"):
        return "~~" + body.strip() + "~~"
    if tag == "a":
        href = node.attrs.get("href", "")
        label = body.strip() or href
        return label if href.startswith("#") else "[" + label + "](" + href + ")"
    return body


def code_block(node):
    language = ""
    body = node
    code = find_one(node, "code")
    if code is not None:
        body = code
        for cls in code.classes() + node.classes():
            if cls.startswith("language-"):
                language = cls[len("language-"):]
    text = plain(body).strip("\n")
    fence = "```"
    while fence in text:
        fence += "`"
    return fence + language + "\n" + text + "\n" + fence


def table_block(node):
    rows = []
    for tr in find_all(node, "tr"):
        cells = [squeeze(plain(cell)).strip() for cell in find_all(tr, "th") + find_all(tr, "td")]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    head, rest = rows[0], rows[1:]
    lines = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rest]
    return "\n".join(lines)


def list_block(node):
    ordered = node.tag == "ol"
    lines = []
    for index, item in enumerate([c for c in node.children if c.tag == "li"], start=1):
        marker = str(index) + ". " if ordered else "- "
        lines.append(marker + " ".join(block_text(item, inline_only=True).split()))
    return lines


def block_text(node, inline_only=False):
    if inline_only:
        return inline(node).strip()
    return "\n\n".join(blocks(node))


def blocks(node):
    """把一个节点下面的内容拆成 Markdown 块。"""
    out = []
    buffer = []

    def flush():
        if buffer:
            text = re.sub(r"[ \t]+\n", "\n", "".join(buffer)).strip()
            if text:
                out.append(text)
            buffer.clear()

    for child in node.children:
        if child.text is not None:
            if child.text.strip():
                buffer.append(child.text)
            continue
        tag, cls = child.tag, child.classes()
        if "post-tags" in cls or tag == "footer":
            continue
        if tag in BLOCK_TAGS:
            flush()
            if tag in HEADINGS:
                out.append("#" * HEADINGS[tag] + " " + " ".join(inline(child).split()))
            elif tag in ("ul", "ol"):
                out.extend(list_block(child))
            elif tag == "blockquote":
                quote = " ".join(block_text(child).split())
                out.append("\n".join("> " + line for line in quote.splitlines() or [quote]))
            elif tag == "pre":
                out.append(code_block(child))
            elif tag == "hr":
                out.append("---")
            elif tag == "table":
                out.append(table_block(child))
            elif tag == "li":
                out.append("- " + " ".join(inline(child).split()))
            else:
                out.extend(blocks(child))
        else:
            buffer.append(inline(child))
    flush()
    return [item for item in out if item]


def to_markdown(body):
    text = "\n\n".join(blocks(body))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# --------------------------------------------------------------------------- #
# 逐篇提取
# --------------------------------------------------------------------------- #
def yaml_value(value):
    """YAML 双引号标量，转义反斜杠与双引号。"""
    escaped = value.replace(BACKSLASH, BACKSLASH * 2).replace('"', BACKSLASH + '"')
    return '"' + escaped + '"'


def parse_page(path):
    tree = Tree()
    tree.feed(path.read_text(encoding="utf-8"))
    root = tree.root

    title_node = find_one(root, "h1", "post-title")
    title = " ".join(plain(title_node).split()) if title_node else path.parts[-2]

    time_node = find_one(root, "time")
    date = updated = ""
    if time_node is not None:
        stamp = time_node.attrs.get("datetime", "")
        if stamp:
            date = stamp.replace("T", " ")[:19]
        found = re.search(r"修改时间[：:]\s*([\d\- :]+)", time_node.attrs.get("title", ""))
        if found and stamp:
            updated = (stamp[:10] + " " + found.group(1).strip())[:19]

    canonical = [n for n in find_all(root, "link") if n.attrs.get("rel") == "canonical"]
    url = canonical[0].attrs.get("href", "") if canonical else ""

    tags = []
    tag_box = find_one(root, "div", "post-tags")
    if tag_box is not None:
        for anchor in find_all(tag_box, "a"):
            name = " ".join(plain(anchor).split()).lstrip("#").strip()
            if name and name not in tags:
                tags.append(unquote(name))

    metas = [n for n in find_all(root, "meta") if n.attrs.get("name") == "description"]
    description = html.unescape(metas[0].attrs.get("content", "")).strip() if metas else ""
    if len(description) > 120:
        description = description[:120].rstrip() + "…"

    body = find_one(root, "div", "post-body")
    relative = path.parent.as_posix().removesuffix("/index.html")
    return {
        "title": title,
        "date": date,
        "updated": updated,
        "url": url or SITE + "/" + relative + "/",
        "tags": tags,
        "description": description,
        "markdown": to_markdown(body) if body is not None else "",
        "relative": relative,
        "slug": relative.split("/")[-1],
    }


def post_path(post, root):
    year = post["date"][:4] or post["relative"][:4]
    day = post["date"][:10] or post["relative"][:10]
    return root / "posts" / year / (day + "-" + post["slug"] + ".md")


def write_post(post, root):
    target = post_path(post, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "title: " + yaml_value(post["title"]), "date: " + yaml_value(post["date"])]
    if post["updated"]:
        lines.append("updated: " + yaml_value(post["updated"]))
    if post["tags"]:
        lines.append("tags: [" + ", ".join(yaml_value(tag) for tag in post["tags"]) + "]")
    lines.append("source: " + post["url"])
    if post["description"]:
        lines.append("description: " + yaml_value(post["description"]))
    lines += ["---", "", post["markdown"].rstrip(), ""]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_index(posts, root):
    target = root / "posts" / "INDEX.md"
    lines = [
        "# 文章清单",
        "",
        "共 " + str(len(posts)) + " 篇，由 `tools/extract_posts.py` 从线上站点提取生成。",
        "「文章」列是仓库里的 Markdown，「原文」列是线上页面。",
        "",
    ]
    years = sorted({post["date"][:4] for post in posts}, reverse=True)
    for year in years:
        group = sorted((p for p in posts if p["date"][:4] == year), key=lambda p: p["date"])
        lines += [
            "## " + year + " 年（" + str(len(group)) + " 篇）",
            "",
            "| 日期 | 标题 | 标签 | 文章 | 原文 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for post in group:
            relative = year + "/" + post["date"][:10] + "-" + post["slug"] + ".md"
            tag_text = "、".join(post["tags"]) or "—"
            lines.append(
                "| " + post["date"][:10] + " | " + post["title"] + " | " + tag_text
                + " | [" + relative + "](" + relative + ") | [线上](" + post["url"] + ") |"
            )
        lines.append("")
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser(description="从已发布的站点里提取文章 Markdown")
    parser.add_argument("--root", default=".", help="仓库根目录（默认当前目录）")
    parser.add_argument("--check", action="store_true", help="只报告，不写文件")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    pages = sorted(root.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*/index.html"))
    if not pages:
        print("没有在 " + str(root) + " 下找到文章页面", file=sys.stderr)
        return 1

    posts = []
    for page in pages:
        post = parse_page(page)
        if not post["markdown"]:
            print("  !! 正文为空：" + post["relative"], file=sys.stderr)
        posts.append(post)

    print("找到 " + str(len(posts)) + " 篇文章")
    for post in sorted(posts, key=lambda p: p["date"]):
        tags = ", ".join(post["tags"]) or "无标签"
        print("  " + post["date"][:10] + "  " + post["title"] + "  [" + tags + "]  "
              + str(len(post["markdown"])) + " 字符")

    if args.check:
        print("")
        print("--check：没有写任何文件")
        return 0

    for post in posts:
        write_post(post, root)
    index = write_index(posts, root)
    print("")
    print("已写入 posts/ 与 " + index.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
