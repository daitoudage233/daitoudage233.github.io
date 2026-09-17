#!/usr/bin/env python3
"""生成站点的「目录」页：/catalog/。

这个仓库是 Hexo 生成好的静态站点：首页只显示最近几篇，`/archives/` 又被拆成了每页一篇
（还混着上一次生成留下的旧页），当目录用都不顺手。所以这里自己生成一个单页目录，
把全部文章按年份倒序列出来，并在导航菜单里加上入口。

脚本可以反复执行，不会重复插入菜单：

    1. 用 archives/index.html 当模板生成 catalog/index.html；
    2. 给所有页面的导航菜单加上「目录」入口；
    3. 顺手把侧栏和归档页里过期的文章数改对（生成时写的是 17，实际篇数按站点里真实的
       文章页统计）。

用法（在仓库根目录）：
    python3 tools/make_catalog.py
    python3 tools/make_catalog.py --check     # 只报告会改什么，不写文件
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys
from urllib.parse import quote

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import extract_posts

TEMPLATE = "archives/index.html"
CATALOG = "catalog/index.html"
MENU_ANCHOR = '    <a href="/archives/" rel="section"><i class="fa fa-archive fa-fw"></i>归档</a>\n\n  </li>\n'
MENU_ITEM = (
    '        <li class="menu-item menu-item-catalog">\n\n'
    '    <a href="/catalog/" rel="section"><i class="fa fa-list-ul fa-fw"></i>目录</a>\n\n'
    '  </li>\n'
)
CONTENT_START = '<div class="content archive">'


def collect_posts(root: pathlib.Path):
    pages = sorted(root.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*/index.html"))
    posts = []
    for page in pages:
        post = extract_posts.parse_page(page)
        post["path"] = post["url"].replace(extract_posts.SITE, "")
        posts.append(post)
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def build_content(posts):
    years = []
    for post in posts:
        year = post["date"][:4]
        if year not in years:
            years.append(year)

    lines = [
        '          <div class="content archive">',
        '            <div class="post-block">',
        '              <div class="posts-collapse">',
        '                <div class="collection-title">',
        '                  <span class="collection-header">全部 ' + str(len(posts)) + ' 篇文章'
        + "".join("　|　" + y + " 年 " + str(sum(1 for p in posts if p["date"][:4] == y)) + " 篇" for y in years)
        + '　|　点标题直达原文</span>',
        '                </div>',
    ]

    counts = {}
    for post in posts:
        for tag in post["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    if counts:
        links = [
            '<a href="/tags/' + quote(tag) + '/">' + html.escape(tag) + '</a>（' + str(n) + ' 篇）'
            for tag, n in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
        lines += [
            '                <div class="collection-title">',
            '                  <span class="collection-header">标签：' + "　".join(links) + '</span>',
            '                </div>',
        ]

    for year in years:
        lines += [
            '',
            '<div class="collection-year">',
            '  <span class="collection-header">' + year + '</span>',
            '</div>',
        ]
        for post in (p for p in posts if p["date"][:4] == year):
            lines += [
                '',
                '<article itemscope itemtype="http://schema.org/Article">',
                '  <header class="post-header">',
                '',
                '    <div class="post-meta">',
                '      <time itemprop="dateCreated" datetime="' + post["date"][:10]
                + '" content="' + post["date"][:10] + '">' + post["date"][5:10] + '</time>',
            ]
            for tag in post["tags"]:
                lines.append(
                    '      <span class="post-meta-item"><i class="fa fa-tag fa-fw"></i>'
                    + html.escape(tag) + '</span>'
                )
            lines += [
                '    </div>',
                '',
                '    <div class="post-title">',
                '      <a class="post-title-link" href="' + post["path"] + '" itemprop="url">',
                '        <span itemprop="name">' + html.escape(post["title"]) + '</span>',
                '      </a>',
                '    </div>',
                '',
                '  </header>',
                '</article>',
            ]

    # 注意：内容区最外层的 </div> 由模板提供（替换区域到分页 </nav> 为止），这里不要重复输出
    lines += ['', '              </div>', '            </div>']
    return "\n".join(lines) + "\n"


def replace_content(page, content):
    start = page.index(CONTENT_START)
    pagination = page.find('<nav class="pagination">', start)
    if pagination != -1:
        end = page.index("</nav>", pagination) + len("</nav>")
    else:
        end = page.index("\n\n\n          </div>", start)
    return page[:start] + content.rstrip("\n") + page[end:]


def build_page(template, posts):
    page = template
    page = re.sub(r"<title>.*?</title>", "<title>目录 | 时光啊时光</title>", page, count=1, flags=re.S)
    page = re.sub(r'(<link rel="canonical" href=")[^"]*(")', r"\g<1>" + extract_posts.SITE + r"/catalog/\g<2>", page, count=1)
    page = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r"\g<1>" + extract_posts.SITE + r"/catalog/\g<2>", page, count=1)
    page = re.sub(r'(<meta property="og:title" content=")[^"]*(")', r"\g<1>目录\g<2>", page, count=1)
    page = page.replace("<span>2023</span>", "<span>2023</span>")
    return replace_content(page, build_content(posts))


def patch_menus(root, check):
    changed = []
    for page in sorted(root.rglob("*.html")):
        if ".git" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        if 'href="/catalog/" rel="section"' in text:
            continue
        if MENU_ANCHOR not in text:
            print("  !! 找不到菜单锚点，跳过：" + page.as_posix(), file=sys.stderr)
            continue
        changed.append(page)
        if not check:
            page.write_text(text.replace(MENU_ANCHOR, MENU_ANCHOR + MENU_ITEM, 1), encoding="utf-8")
    return changed


def patch_counts(root, total, check):
    changed = []
    pattern = re.compile(r'(<span class="site-state-item-count">)\d+(</span>\s*<span class="site-state-item-name">日志</span>)')
    header = re.compile(r"共计 \d+ 篇日志")
    for page in sorted(root.rglob("*.html")):
        if ".git" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        new = pattern.sub(lambda m: m.group(1) + str(total) + m.group(2), text)
        new = header.sub("共计 " + str(total) + " 篇日志", new)
        if new != text:
            changed.append(page)
            if not check:
                page.write_text(new, encoding="utf-8")
    return changed


def main():
    parser = argparse.ArgumentParser(description="生成站点目录页 /catalog/ 并加上菜单入口")
    parser.add_argument("--root", default=".", help="仓库根目录（默认当前目录）")
    parser.add_argument("--check", action="store_true", help="只报告，不写文件")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    template_path = root / TEMPLATE
    if not template_path.is_file():
        print("找不到模板 " + TEMPLATE, file=sys.stderr)
        return 1

    posts = collect_posts(root)
    print("文章：" + str(len(posts)) + " 篇")

    target = root / CATALOG
    content = build_page(template_path.read_text(encoding="utf-8"), posts)
    if not args.check:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print("目录页：" + CATALOG + "（" + str(len(content)) + " 字符）")

    menus = patch_menus(root, args.check)
    print("加菜单入口的页面：" + str(len(menus)))

    counts = patch_counts(root, len(posts), args.check)
    print("修正文章篇数的页面：" + str(len(counts)))

    if args.check:
        print("")
        print("--check：没有写任何文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
