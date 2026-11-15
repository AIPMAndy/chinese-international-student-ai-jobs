# GitHub Pages 部署

部署要求更新：2026-11-13。用户已明确授权推送本项目，正式网站使用 GitHub Pages。

## 正式目标

- 仓库：`AIPMAndy/chinese-international-student-ai-jobs`。
- 分支：`main`。
- 工作流：`.github/workflows/pages.yml`。
- 静态目录：`dist/`。
- 正式项目地址：[https://aipmandy.github.io/chinese-international-student-ai-jobs/](https://aipmandy.github.io/chinese-international-student-ai-jobs/)。已由 Pages 成功部署返回值和发布后 HTTP 检查确认。

已确认公开仓库、`main`、Pages 部署和线上下载。以下记录绑定具体验收提交；后续更新以对应工作流结果为准。正式网站使用本项目的 GitHub Pages。

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

自 2026-11-14 起，Pages 工作流从最新源代码、Markdown、研究资料与网站资产重新生成 dist，再重新打包源码/模板/网站 ZIP；执行 SEO 和 Pages 链接检查，部署同一构建环境的产物，并对 10 个线上 URL 逐一进行 HTTP 200、文件签名和 SHA-256 读回校验。PDF 二进制继续来自 pdf/ 且本轮未改正文；若修改了正文，先执行 PDF 的源文档生成与视觉 QA。仓库中的 dist 只是之前构建的快照，不可用旧 SHA 代替新上线产物。

工作流限制为本项目精确仓库的 `main`，支持 push 和手动触发，使用 `github-pages` 环境。全局仅授予 `contents: read`，部署任务额外取得 `pages: write` 和 `id-token: write`。

## 线上验收记录

| 项目 | 状态 |
| --- | --- |
| 远端仓库可访问 | 2026-11-14 已确认公开且可写 |
| 验收提交 SHA | `6e125466cc1a48567564e514912227685d33381e` |
| Pages Actions 成功运行链接 | [运行 43472027896](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/actions/runs/43472027896)：completed / success |
| 实际网站 URL | [https://aipmandy.github.io/chinese-international-student-ai-jobs/](https://aipmandy.github.io/chinese-international-student-ai-jobs/)，与部署返回值一致 |
| 首页、岗位页、地区页、PDF / ZIP 线上检查 | 此运行的 6 项发布后 HTTP 检查全部通过；HTML、PDF 和两个 ZIP 的文件签名符合预期 |
| 手机页面与关键交互检查 | 本次部署复核未重做实体手机或浏览器交互测试；既有验证记录见 VALIDATION.md，不能把 HTTP 检查当作手机实测 |

## 官方依据

核验日：2026-11-13。

- [GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [配置 Pages 发布源](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 2026-11-14 · 源码驱动发布复核

- 新增：每页 canonical、Open Graph、合法 JSON-LD（WebPage、作者、公司）、robots 和完整 sitemap；增加 [咨询与陪跑](https://metaver.vip/services) 入口，保留原有搜索、JD 筛选、自查与教学代码。
- [生成器提交 9a33276](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/commit/9a3327631038c1bfe1caf1138371538db9c3db06)、[SEO 测试 a1015d5](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/commit/a1015d51b5bf0f7d6fe1221ab673ec3776fac184)、[Pages 验证提交 7bfe19c](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/commit/7bfe19ccc19ba8f443a5a4e8d46c76ddfb0857b6)。[Pages #43520404300](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/actions/runs/43520404300) 成功：52 页 SEO 元数据检查零错误；首页、岗位、地区、PDF、两个 ZIP、sitemap、robots、CSS、JS 共 10 个线上资源 HTTP 200，SHA-256 与该轮生成产物相同。
- 初始教学 CI 因提交后的旧源码 ZIP 与源文件版本不一致报出 stale input，已修正为先执行教学案例/风险测试，再从源码生成站点与归档，最后核对完整性。[修正提交 0785a74](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/commit/0785a7434cf5a8989de629261b8ade4b75fa5167) 和 [教学 CI #43520496459](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/actions/runs/43520496459) 已成功，未跳过原测试。
- PDF 当前在线 SHA-256：f07ee347ff51ccb8e6a870cf6ed178065384262aa39937985cdd081682e14d0e，973178 字节；与 [109 页视觉 QA](pdf/visual-review.json) 的 SHA 一致。PDF 正文未修改。
- 最终提交 [0785a74 对应 Pages 运行](https://github.com/AIPMAndy/chinese-international-student-ai-jobs/actions/runs/43520496423) 需再记录成功与 HTTP 结果。移动 Safari / 安卓及新近政策独立复核待完成，项目暂不标全部 DONE。
