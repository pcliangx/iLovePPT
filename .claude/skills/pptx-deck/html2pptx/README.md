# html2pptx(vendored)

`html2pptx.js` + `html2pptx_cli.js` **vendored 自 [icip-cas/PPTAgent](https://github.com/icip-cas/PPTAgent) 的 `deeppresenter/html2pptx/`**(ACL 2026 DeepPresenter)。iLovePPT 的 **html 轨**(designer track=html)用它把每页 HTML(+ global.css)转 `.pptx`。

## 归属 / 许可

- 上游:`deeppresenter/html2pptx/` © PPTAgent 贡献者
- 许可:遵循上游 PPTAgent repo 的 LICENSE(使用本 vendored 副本须同时遵守上游许可)
- 本地改动:**未修改**上游 `html2pptx.js` / `html2pptx_cli.js` / `package.json`(逐字 vendor);改动需求请走上游 PR,不在此处 fork

## 依赖(setup · html 轨才需要)

```bash
cd .claude/skills/pptx-deck/html2pptx
npm install              # playwright + pptxgenjs + sharp + fast-glob + minimist
npx playwright install chromium   # 浏览器(html2pptx 用 Chromium 渲染 HTML + CDP 字体检测)
```

> 仅 **html 轨**需要这些依赖;pptx / lark-slides / lark-whiteboard 三轨零 Node 依赖。brainstorm track 可行性 gate(Step 0)会查 `node` + `npx playwright --version`,缺则建议换轨。

## 用法(designer track=html 调)

```bash
node .claude/skills/pptx-deck/html2pptx/html2pptx_cli.js \
     --html_dir <working_dir>/builder/slides \
     --output <working_dir>/builder/deck_v{N}.pptx \
     --layout 16:9
```

输入:`slides/slide_NN.html`(`<body>` 固定 1280×720 · `<link rel="stylesheet" href="global.css">` · `<body data-theme="<theme>">`)+ `global.css`(由 `themes/theme2css.py` 生成)。
输出:`.pptx`(pptxgenjs 构造 · 渐变/阴影经 Playwright 光栅化为 PNG 嵌入 · CDP 抓真实渲染字体保真)。

失败回退:designer 用 soffice 直接转 HTML→PDF→pptx(质量降,但无 Node 也能出)。
