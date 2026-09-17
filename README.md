# daitoudage233.github.io

个人博客「时光啊时光」的站点仓库 —— 由 [Hexo](https://hexo.io/) 生成后部署，[GitHub Pages](https://pages.github.com/) 直接托管。

线上地址：**https://daitoudage233.github.io**

## 仓库里有什么

| 路径 | 说明 |
| --- | --- |
| `index.html`、`page/` | 首页与分页 |
| `2022/`、`2023/` | 文章正文页，路径形如 `<年>/<月>/<日>/<标题>/index.html` |
| `archives/` | 归档页（按年、按月，带分页） |
| `tags/` | 标签页 |
| `catalog/` | **目录页**：一页列出全部 35 篇文章，<https://daitoudage233.github.io/catalog/> |
| `css/`、`js/`、`lib/`、`images/` | NexT 主题的样式、脚本与图标 |
| `calendar.json` | 侧边栏日历的数据文件 |
| `.nojekyll` | 告诉 GitHub Pages 原样发布这些文件，不要再套一层 Jekyll 处理 |
| `posts/` | **文章正文的 Markdown 版本**（见下一节） |
| `tools/extract_posts.py` | 生成 `posts/` 的提取脚本 |
| `tools/make_catalog.py` | 生成 `catalog/` 目录页，并给所有页面加上菜单入口 |

共 **35 篇文章**：2022 年 31 篇，2023 年 4 篇。

## 关于 posts/

这个仓库是 `hexo generate` 的产物：只有生成好的 HTML，没有 Hexo 源码，源码也不在这个仓库里。
HTML 不好读、不好改、也没法全文搜索，所以 `tools/extract_posts.py` 把每篇文章的正文从 HTML
里反向提取成了 Markdown，整理在一起：

```
posts/
├── INDEX.md     全部 35 篇的清单：日期 / 标题 / 标签 / 仓库内文件 / 线上原文
├── 2022/        2022 年的 31 篇，文件名形如 2022-05-18-农民.md
└── 2023/        2023 年的 4 篇
```

每篇都带 front matter（标题、创建与修改时间、标签、线上原文地址、摘要）：

```yaml
---
title: "农民"
date: "2022-05-18 21:41:12"
updated: "2022-05-18 21:45:03"
tags: ["前几天的文章"]
source: https://daitoudage233.github.io/2022/05/18/%E5%86%9C%E6%B0%91/
description: "……"
---
```

用法（在仓库根目录，只需要 Python 3，不用装任何第三方库）：

```sh
python3 tools/extract_posts.py            # 提取或刷新 posts/
python3 tools/extract_posts.py --check    # 只统计每篇的日期、标题、标签和字数，不写文件
```

脚本只读取 `2022/`、`2023/` 目录下的 `index.html`，**不会改动已经发布的站点**，线上页面照旧可访问。

## 关于 catalog/：目录页

站点自带的 `/archives/` 被生成成了「每页一篇」（还混着上一次生成留下的旧页），翻起来很费劲，
所以 `tools/make_catalog.py` 另外生成了一个单页目录 `catalog/index.html`：按年份倒序列出全部文章，
每篇带日期、标签和直达链接，顶部还有篇数统计和标签索引。脚本同时做两件事：

```sh
python3 tools/make_catalog.py            # 生成/刷新 catalog/，给所有页面加菜单入口
python3 tools/make_catalog.py --check    # 只报告会改什么，不写文件
```

- 给所有页面的导航菜单加上「目录」入口（已经有的会跳过，可以反复执行）；
- 顺手把侧栏和归档页里过期的篇数改对：生成时写的是 17，实际是 35 篇。

导航里现在是这样：**首页 · 归档 · 目录**。

## 站点是怎么搭的

- 博客框架：Hexo 6.1.0（页面里的 `<meta name="generator">` 写着版本号）
- 主题：NexT 7.8.0，Gemini 配色
- 部署：GitHub Pages 直接托管本仓库 `main` 分支的根目录，提交信息是 Hexo 的 `Site updated: ...`
- 根目录的 `.nojekyll` 会跳过 GitHub Pages 的 Jekyll 处理：这些页面本来就是 Hexo 生成好的静态文件，
  原样发布即可，也免得以后新增的文件被 Jekyll 重新渲染一遍
- 站点名：时光啊时光 · 作者：带头大哥23b
- 最后一次生成：2023-03-26

页面用到的字体图标、Fancybox 等前端库都在 `lib/` 下。Hexo 与 NexT 主题都是 MIT 许可的开源项目，
站点的样式和排版基本都来自它们，这里一并致谢；包内的许可与出处见各自目录。

## 想继续更新的话

1. **改内容**：编辑 `posts/` 里对应的 Markdown，或者用这些 Markdown 把 Hexo 站点恢复出来
   （正文和 front matter 放进 `source/_posts/` 就能直接用）。
2. **重新生成**：装好 Hexo 与 NexT 主题后 `hexo generate`，把生成结果覆盖到仓库根目录再提交。
   新增的文章页提交后，再跑一次 `python3 tools/make_catalog.py` 就能出现在目录页里。
3. 只想改个错别字也可以直接改对应的 `index.html`，但下次重新生成会被覆盖，所以还是推荐走前两步。

## 版权

文章多为随笔、散文摘录和技术笔记，文字版权归各自作者所有；`lib/` 下的前端库与 NexT 主题
遵循它们各自的许可（MIT）。提取脚本 `tools/extract_posts.py` 可以随意取用。
