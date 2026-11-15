# PDF 成品与重建

作者：AI酋长Andy · 星觉科技 · 北京 · 微信号：AIPMAndy  
版本：2026-11-13。

成品文件：`chinese-international-student-ai-jobs-guide.pdf`。

## 内容来源

生成脚本直接读取当前仓库文件，不把旧正文快照硬编码在脚本中：

- `docs/00-start.md` 至 `09-review-and-next-steps.md`，以及 `technical-case-studies.md`。
- 三个 `examples/*/README.md` 的完整输入、方法、命令、预期结果、错误排查与限制。
- `research/employer-jds.md`、`regional-rules.md`、`coverage-gaps.md`、`technical-sources.md`。
- `templates/*.md` 的全部现有模板。
- `assets/operation-home.jpg`、`assets/operation-results.jpg` 的真实浏览器截图；也支持同名 PNG/JPEG，优先读取 JPG。

PDF 包含封面、使用与版本说明、可点击目录和书签、矢量岗位路线图、完整实操正文、技术手册、岗位与地区资料、模板、实际截图、原始链接索引和页码。宽表在必要时变成逐条字段卡片，保留全部单元格信息。超长代码会视觉折行，并提示读者复制源文件中的完整原文。

已收录的章节使用 PDF 内部跳转；其他相对文件目标与长行代码的原文位置显示为“源码包内：相对路径”。读者从配套源码 ZIP 解压后打开对应文件；不生成尚未发布的仓库或网站外链。官方来源链接保留。`source-links.json` 记录实际引用的源码包路径及本地文件存在性，不含待上线源码链接。

## 重建环境

Python 3.10+，需要 `reportlab`、`fonttools`、`pypdf`、`Pillow`。可在独立虚拟环境安装这些 PDF 制作依赖：

本次实际环境：Python 3.12.14、ReportLab 4.4.9、fonttools 4.61.1、pypdf 6.21.4、Pillow 13.0.0。

```bash
python3 -m venv .venv-pdf
.venv-pdf/bin/python -m pip install reportlab fonttools pypdf Pillow
.venv-pdf/bin/python scripts/build_pdf.py
```

Windows 可使用 `py -3 -m venv .venv-pdf`，虚拟环境解释器路径改为 `.venv-pdf\Scripts\python.exe`。这些依赖**只用于制作 PDF**；三个教学项目仍只依赖 Python 标准库。

默认字体路径：

```text
/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
```

脚本选取 Noto CJK 字体集合中的简体中文分面（索引 2），按实际使用字符把 CFF 轮廓转换为二次曲线 TrueType 缓存，再由 ReportLab 子集嵌入 PDF。字体缓存放在 `tmp/pdf-build/`，无需提交。所有实际正文与标题使用嵌入的中文字体；来源字体采用 SIL Open Font License，派生字体重命名为 GuideSC。

实际使用的两个字体分面、字体内版权信息、文件 SHA-256 和系统发行版完整许可通知保存在 [THIRD-PARTY-FONTS.txt](THIRD-PARTY-FONTS.txt)。临时转换字体不随项目分发。

其他系统可指向已安装、包含所需中文字形的字体：

```bash
python3 scripts/build_pdf.py --font-regular /path/to/regular.ttf --font-bold /path/to/bold.ttf
```

若使用其他 TTC，需同时确认 `--font-number` 对应的分面。不可用缺少中文字形的西文字体代替。

## 生成并渲染全部页面

系统安装 Poppler，保证 `pdftoppm` 和 `pdfinfo` 可用后：

```bash
python3 scripts/build_pdf.py --render
pdfinfo pdf/chinese-international-student-ai-jobs-guide.pdf
```

`--render` 会在 `tmp/pdf-pages/` 保存每页 65 dpi PNG，并在 `tmp/pdf-contact-sheets/` 生成每张六页的联系表，用于逐页检查整体排版。对封面、表格、来源 URL、代码和截图再用 120–150 dpi 放大复核。

```bash
pdftoppm -f 1 -l 1 -r 150 -png pdf/chinese-international-student-ai-jobs-guide.pdf tmp/pdf-cover
```

截图不存在时脚本会跳过，并在 `build-report.json` 中明确列出实际加入的图片。正式发布前应确认两张真实截图均被包含，不能把示意图或未执行结果当截图。

## 验收记录

`build-report.json` 每次重建都会更新页数、字节数、内容源文件和 SHA-256、截图 SHA-256、链接数量、品牌文本检查与生成时间。它不是“已经人工看过全部页面”的证明。

`visual-review.json` 记录本次实际逐页视觉检查的版本与文件哈希。正文或截图有变动、PDF 重新生成后，应重新渲染检查，更新该记录；不要复用旧版“已通过”结论。

主要检查：中文不缺字，文本和表格不越界，长链接可点击，代码折行有说明，目录跳转和页码正确，真实截图清晰，章节没有无意义的近空白尾页。PDF 中的地区与雇主状态仍以正文标注为准，排版验收不等于事实永久有效。
