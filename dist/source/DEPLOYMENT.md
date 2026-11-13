# GitHub Pages 部署

部署要求更新：2026-11-13。用户已明确授权推送本项目，正式网站使用 GitHub Pages。

## 正式目标

- 仓库：`AIPMAndy/chinese-international-student-ai-jobs`。
- 分支：`main`。
- 工作流：`.github/workflows/pages.yml`。
- 静态目录：`dist/`。
- 预期项目地址：`https://aipmandy.github.io/chinese-international-student-ai-jobs/`。**此地址待发布，不代表已经上线。** 最终以部署返回值与实际访问结果为准。

本文件未记录已验证的远端提交和 Pages 线上验收结果。ChatGPT Pages / Sites 不作为本项目的正式部署目标。

## 发布步骤

1. 确认 GitHub 账号为 AIPMAndy，且上述仓库存在并可写。不存在时创建同名公开空仓库；不覆盖已有仓库。
2. 完成网站和下载打包，保证以下文件非空：
   - `dist/downloads/chinese-international-student-ai-jobs-guide.pdf`
   - `dist/downloads/templates.zip`
   - `dist/downloads/chinese-international-student-ai-jobs-source.zip`
3. 在项目根目录检查提交中的静态网站：

```bash
python3 scripts/check_pages_links.py --require downloads/chinese-international-student-ai-jobs-guide.pdf --require downloads/templates.zip --require downloads/chinese-international-student-ai-jobs-source.zip
```

检查脚本仅使用 Python 标准库，按仓库子路径解析本地 HTML 链接、锚点与 CSS 资源，也检查 PDF / ZIP 文件是否存在。它不验证外部来源、JavaScript 动态加载、交互或真实线上状态。

4. 完成原有内容、案例、PDF 和浏览器验收。实际打开手机与桌面页面，验证目录、搜索、模板、PDF、源码下载、微信复制和官网入口。
5. 将本项目源码、交付物、`dist/`、本部署规范及工作流提交并推送到目标仓库 `main`。确认成品下载未因忽略规则漏掉。不得在源码、提交或远端 URL 写入凭据。
6. 在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。之后由 `main` 推送触发工作流，也可手动运行。
7. 等待部署成功，实际打开工作流返回的网站地址，核验首页 HTTP 200、子路径资源、章节、PDF / ZIP 和手机阅读。完成后再将 README 的网站标为已上线。

## 部署已验收产物

工作流检查并上传提交中的 `dist/`。发布阶段不重新生成中文 PDF，也不执行依赖当前工作区路径的构建。内容修改后先按项目原有构建说明更新和验收 `dist/`，再提交；这样部署的文件与本地验收对象一致。

工作流限制为本项目精确仓库的 `main`，支持 push 和手动触发，使用 `github-pages` 环境。全局仅授予 `contents: read`，部署任务额外取得 `pages: write` 和 `id-token: write`。

## 线上验收记录

| 项目 | 状态 |
| --- | --- |
| 远端仓库可访问 | 2026-11-14 已确认公开且可写 |
| 推送提交 SHA | 待记录 |
| Pages Actions 成功运行链接 | 待记录 |
| 实际网站 URL | 待部署返回与访问确认 |
| 首页、章节、PDF / ZIP 线上检查 | 待完成 |
| 手机页面与关键交互检查 | 待完成 |

## 官方依据

核验日：2026-11-13。

- [GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [配置 Pages 发布源](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
