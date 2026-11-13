# 发布与重建

版本：1.0.0，2026-11-13。作者：AI 酋长 Andy。

## 本版状态

GitHub 公开仓库：[AIPMAndy/chinese-international-student-ai-jobs](https://github.com/AIPMAndy/chinese-international-student-ai-jobs)。2026-11-14 已确认仓库可访问且可写。完整正文、代码、PDF、模板与静态网站已在本地准备同步；远程完整提交、Pages 部署与线上访问分别验收。

2026-11-13 用户已明确指定正式配套网站使用 **GitHub Pages**，并授权直接推送本项目。发布前必须先读 [DEPLOYMENT.md](DEPLOYMENT.md)。目标仓库为 `AIPMAndy/chinese-international-student-ai-jobs`，预期项目地址为 `https://aipmandy.github.io/chinese-international-student-ai-jobs/`；该地址待发布，最终以部署返回值及实际访问验收为准。ChatGPT Pages / Sites 不作为本项目的正式网站。源码、PDF与模板由配套静态站提供。

## 本地运行与构建

```bash
python3 examples/run_all.py
python3 scripts/build_site.py --repo-url https://github.com/AIPMAndy/chinese-international-student-ai-jobs
python3 scripts/build_pdf.py
python3 scripts/package_release.py
python3 scripts/build_site.py --repo-url https://github.com/AIPMAndy/chinese-international-student-ai-jobs
python3 scripts/package_release.py
python3 scripts/check_release.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

技术例子、网站构建、打包和内容校验仅使用 Python 标准库。PDF构建另需 reportlab、fonttools 与 Noto CJK 字体，见 pdf/README.md。已提供成品 PDF，普通读者不必安装排版依赖。

网站为 `dist/` 下的静态文件，无账号、无用户数据上传、无分析埋点。源码包解压后运行上述构建命令，再访问 http://127.0.0.1:8080/。本地服务器运行时可断网阅读、搜索和自查；直接以 file:// 打开页面不保证全文检索可用。联网只在读者主动打开外部来源时发生。源码ZIP不递归包含其自身，解压后须重新生成下载区。第二次打包使源码包内的网页与已启用下载状态一致。

## GitHub 发布的必要步骤

将已验收的本项目完整目录同步至现有公开仓库 `AIPMAndy/chinese-international-student-ai-jobs` 的 main 分支；不要重新创建同名仓库，不改动其他仓库。可以使用标准 Git 或已经授权的 GitHub 连接；不要把 token 写进源码、脚本或远端 URL。

仓库 Settings → Pages 的 Source 使用 GitHub Actions，用户已确认开启。仓库附有 `.github/workflows/pages.yml`；提交后等待该工作流成功，并实际打开返回的网站地址。构建时 `--repo-url` 使用上方已验证的仓库地址；页面 canonical 使用正式 GitHub Pages 目标，并不代表部署已经成功。工作流源于 [GitHub官方文档](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)，核验于2026-11-13。

GitHub Actions 工作流已经准备，但本版尚无GitHub远端工作流成功运行记录；不能把本地样例测试写成远端CI已通过。

## 权限与边界

只发布本项目；不修改个人主页、总导航、官网或其他留学生仓库。无需改DNS，无需给其他项目添加入口。品牌联系方式为公开业务信息：微信AIPMAndy、公众号AI酋长Andy、https://metaver.vip/、https://www.a6no1.cn/。
