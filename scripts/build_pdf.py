#!/usr/bin/env python3
"""Build the complete Chinese guide from Markdown sources; no content snapshots.

Dependencies: reportlab, fonttools, pypdf, Pillow. Rendering additionally uses
Poppler (pdftoppm). The runnable teaching examples have no such dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont as SourceFont
from PIL import Image as PillowImage, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, KeepTogether, LongTable,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdf"
TMP = ROOT / "tmp/pdf-build"
PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 51, 51, 58, 50
WIDTH = PAGE_W - LEFT - RIGHT
HEIGHT = PAGE_H - TOP - BOTTOM
VERSION = "2026-11-13"
INK = colors.HexColor("#17201D")
TEAL = colors.HexColor("#126653")
MUTED = colors.HexColor("#66716A")
PAPER = colors.HexColor("#FCFBF7")
TINT = colors.HexColor("#EEF4F0")
LINE = colors.HexColor("#D7DFD8")
SOURCE_LINKS: OrderedDict[str, str] = OrderedDict()
SOURCE_MAP: dict[Path, str] = {}
BUNDLE_PATHS: set[str] = set()
STYLES: dict[str, ParagraphStyle] = {}


def clean(text: str) -> str:
    for character in "\u2010\u2011\u2012\u2013\u2014\u2015":
        text = text.replace(character, "-")
    return text.replace("\u00a0", " ").replace("✅", "[OK]").replace("☐", "[ ]").replace("☑", "[x]")


def slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff\- ]", "", text)
    return re.sub(r"\s+", "-", text)


def file_key(path: Path) -> str:
    return "doc-" + re.sub(r"[^a-zA-Z0-9-]", "-", path.relative_to(ROOT).as_posix())


def source_files() -> list[tuple[str, Path]]:
    required_docs = ("00-start", "01-role-map", "02-gap-and-learning", "03-evidence", "04-project-workflow", "05-portfolio-and-resume", "06-technical-interviews", "07-region-and-eligibility", "08-targeted-applications", "09-review-and-next-steps", "technical-case-studies")
    required = [ROOT / "docs" / f"{name}.md" for name in required_docs]
    required.extend(ROOT / "research" / f"{name}.md" for name in ("employer-jds", "regional-rules", "coverage-gaps", "technical-sources"))
    required.extend(ROOT / f"examples/{name}/README.md" for name in ("01_ml_experiment", "02_model_service", "03_grounded_retrieval"))
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required PDF sources are missing: " + ", ".join(missing))
    documents = [("guide", p) for p in sorted((ROOT / "docs").glob("[0-9][0-9]-*.md"))]
    documents.append(("case", ROOT / "docs/technical-case-studies.md"))
    documents.extend(("project", ROOT / f"examples/{name}/README.md") for name in (
        "01_ml_experiment", "02_model_service", "03_grounded_retrieval"))
    documents.extend(("research", ROOT / f"research/{name}.md") for name in (
        "employer-jds", "regional-rules", "coverage-gaps", "technical-sources"))
    documents.extend(("template", p) for p in sorted((ROOT / "templates").glob("*.md")))
    return [(kind, path) for kind, path in documents if path.is_file()]


def make_ttf(source_path: Path, characters: str, label: str, collection_index: int) -> Path:
    """Convert only used CFF glyphs to a renamed quadratic TrueType font.

    ReportLab cannot embed the CFF outlines inside common Noto CJK TTC files.
    This preserves the source cmap and metrics for the needed glyphs, uses a
    tight curve approximation, and embeds the resulting subset in the PDF.
    """
    digest = hashlib.sha256((str(source_path) + characters + label).encode()).hexdigest()[:16]
    target = TMP / f"GuideSC-{label}-{digest}.ttf"
    if target.exists():
        return target
    source = SourceFont(str(source_path), fontNumber=collection_index if source_path.suffix.lower() == ".ttc" else -1)
    cmap = source.getBestCmap()
    requested = set(ord(c) for c in characters if c not in "\n\r\t")
    missing = sorted(code for code in requested if code not in cmap)
    if missing:
        raise ValueError("Font lacks glyphs: " + " ".join(f"U+{c:04X} {chr(c)}" for c in missing[:40]))
    if "glyf" in source:
        source.close()
        return source_path
    selected_map = {code: cmap[code] for code in requested}
    glyph_names = [".notdef"] + sorted(set(selected_map.values()) - {".notdef"})
    source_glyphs = source.getGlyphSet()
    glyphs = {}
    metrics = {}
    for name in glyph_names:
        pen = TTGlyphPen(source_glyphs)
        converter = Cu2QuPen(pen, max_err=1.0, reverse_direction=True)
        source_glyphs[name].draw(converter)
        glyphs[name] = pen.glyph()
        metrics[name] = source["hmtx"].metrics[name]
    builder = FontBuilder(source["head"].unitsPerEm, isTTF=True)
    builder.setupGlyphOrder(glyph_names)
    builder.setupCharacterMap(selected_map)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=source["hhea"].ascent, descent=source["hhea"].descent, lineGap=source["hhea"].lineGap)
    builder.setupNameTable({"familyName": "GuideSC", "styleName": label,
                           "uniqueFontIdentifier": f"GuideSC-{label}-{digest}",
                           "fullName": f"GuideSC {label}", "psName": f"GuideSC-{label}",
                           "version": "Version 1.0",
                           "copyright": "Derived from Noto Sans CJK; original font copyright retained; SIL Open Font License 1.1",
                           "licenseDescription": "SIL Open Font License, Version 1.1",
                           "licenseInfoURL": "https://openfontlicense.org/"})
    os2 = source["OS/2"]
    builder.setupOS2(sTypoAscender=os2.sTypoAscender, sTypoDescender=os2.sTypoDescender,
                     sTypoLineGap=os2.sTypoLineGap, usWinAscent=os2.usWinAscent,
                     usWinDescent=os2.usWinDescent, usWeightClass=700 if label == "Bold" else 400)
    builder.setupPost()
    builder.setupMaxp()
    builder.save(str(target))
    source.close()
    return target


def register_fonts(files: list[tuple[str, Path]], args: argparse.Namespace) -> None:
    # Include this script so all cover, diagram, captions, and generated labels
    # have glyphs; include ASCII even when a character is absent from sources.
    content = clean(Path(__file__).read_text(encoding="utf-8"))
    content += "".join(clean(path.read_text(encoding="utf-8")) for _, path in files)
    content += "".join(chr(code) for code in range(32, 127))
    content = "".join(sorted(set(content)))
    regular = make_ttf(Path(args.font_regular), content, "Regular", args.font_number)
    bold = make_ttf(Path(args.font_bold), content, "Bold", args.font_number)
    pdfmetrics.registerFont(TTFont("GuideSC", str(regular)))
    pdfmetrics.registerFont(TTFont("GuideSC-Bold", str(bold)))
    pdfmetrics.registerFontFamily("GuideSC", normal="GuideSC", bold="GuideSC-Bold", italic="GuideSC", boldItalic="GuideSC-Bold")
    STYLES.update({
        "body": ParagraphStyle("Body", fontName="GuideSC", fontSize=10.2, leading=16.4, textColor=INK, spaceAfter=6.5, wordWrap="CJK", allowWidows=0, allowOrphans=0),
        "small": ParagraphStyle("Small", fontName="GuideSC", fontSize=8.9, leading=14.2, textColor=MUTED, spaceAfter=6, wordWrap="CJK"),
        "h1": ParagraphStyle("Chapter", fontName="GuideSC-Bold", fontSize=23, leading=32, textColor=INK, spaceAfter=17, keepWithNext=True, wordWrap="CJK"),
        "h2": ParagraphStyle("Heading2", fontName="GuideSC-Bold", fontSize=14.1, leading=21, textColor=TEAL, spaceBefore=12, spaceAfter=7, keepWithNext=True, wordWrap="CJK"),
        "h3": ParagraphStyle("Heading3", fontName="GuideSC-Bold", fontSize=11.3, leading=18, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=True, wordWrap="CJK"),
        "bullet": ParagraphStyle("Bullet", fontName="GuideSC", fontSize=10.1, leading=16.4, textColor=INK, leftIndent=12, firstLineIndent=-10, spaceAfter=4.5, wordWrap="CJK", allowWidows=0, allowOrphans=0),
        "cell": ParagraphStyle("Cell", fontName="GuideSC", fontSize=9.1, leading=14.3, textColor=INK, wordWrap="CJK"),
        "cellhead": ParagraphStyle("CellHead", fontName="GuideSC-Bold", fontSize=9.2, leading=14.4, textColor=colors.white, wordWrap="CJK"),
        "cardlabel": ParagraphStyle("CardLabel", fontName="GuideSC-Bold", fontSize=9.0, leading=14.3, textColor=TEAL, wordWrap="CJK"),
        "caption": ParagraphStyle("Caption", fontName="GuideSC", fontSize=8.8, leading=14.0, textColor=MUTED, spaceBefore=6, spaceAfter=12, wordWrap="CJK"),
        "eyebrow": ParagraphStyle("Eyebrow", fontName="GuideSC-Bold", fontSize=8.4, leading=13, textColor=TEAL, spaceAfter=7, tracking=1.5),
    })


def target_link(url: str, current_file: Path) -> str:
    if url.startswith(("https://", "http://", "mailto:")):
        return url
    if url.startswith("#"):
        return "#" + file_key(current_file) + "-" + slug(url[1:])
    file_part, _, anchor = url.partition("#")
    target = (current_file.parent / file_part).resolve()
    if target in SOURCE_MAP:
        return "#" + SOURCE_MAP[target] + ("-" + slug(anchor) if anchor else "")
    try:
        relative = target.relative_to(ROOT).as_posix()
    except ValueError:
        relative = file_part
    BUNDLE_PATHS.add(relative)
    return "源码包内：" + relative + ("#" + anchor if anchor else "")


def inline(text: str, current_file: Path) -> str:
    text = clean(text)
    saved = []
    def hold(value: str) -> str:
        saved.append(value)
        return f"ZZTOKEN{len(saved) - 1}ZZ"
    def link(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        destination = target_link(url, current_file)
        if destination.startswith("源码包内："):
            readable_label = html.escape(re.sub(r"[`*_]", "", label))
            return hold(f'{readable_label}（<font color="#28574B">{html.escape(destination)}</font>）')
        if url.startswith(("https://", "http://")):
            SOURCE_LINKS.setdefault(url, re.sub(r"[`*_]", "", label))
        return hold(f'<link href="{html.escape(destination, quote=True)}" color="#126653">{html.escape(re.sub(r"[`*_]", "", label))}</link>')
    # Employer URLs can contain balanced parentheses, e.g. SAP's "(fmd)".
    # A negated-right-parenthesis pattern silently truncates such source links.
    text = re.sub(r"\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)", link, text)
    text = re.sub(r"`([^`]+)`", lambda m: hold(f'<font color="#28574B">{html.escape(m.group(1))}</font>'), text)
    def bare_url(match: re.Match) -> str:
        url = match.group(0).rstrip("。；，,.;：）")
        trailing = match.group(0)[len(url):]
        SOURCE_LINKS.setdefault(url, urlparse(url).netloc)
        return hold(f'<link href="{html.escape(url, quote=True)}" color="#126653">{html.escape(url)}</link>') + trailing
    text = re.sub(r"https?://[^\s<>]+", bare_url, text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    for index, value in enumerate(saved):
        text = text.replace(f"ZZTOKEN{index}ZZ", value)
    return text


def paragraph(text: str, path: Path, style: str = "body") -> Paragraph:
    marked_up = inline(text, path)
    if style == "cellhead":
        marked_up = marked_up.replace('color="#126653"', 'color="#FFFFFF"').replace('color="#28574B"', 'color="#FFFFFF"')
    return Paragraph(marked_up, STYLES[style])


class Rule(Flowable):
    def __init__(self, width: float = WIDTH, space: float = 12):
        super().__init__()
        self.width, self.height = width, space
    def draw(self):
        self.canv.setStrokeColor(LINE)
        self.canv.setLineWidth(0.6)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


class CodeBlock(Flowable):
    def __init__(self, text: str, prepared: list[str] | None = None):
        super().__init__()
        self.text = clean(text).expandtabs(4)
        self.prepared = prepared
        self.font_size = 8.6
        self.leading = 13.1
        self.width = WIDTH
        self.lines: list[str] = []
    def wrap(self, available_width: float, available_height: float):
        self.width = min(WIDTH, available_width)
        self.lines = self.prepared if self.prepared is not None else []
        if self.prepared is None:
            for source_line in self.text.splitlines() or [""]:
                current = ""
                for char in source_line:
                    if current and pdfmetrics.stringWidth(current + char, "GuideSC", self.font_size) > self.width - 24:
                        self.lines.append(current)
                        current = "  " + char
                    else:
                        current += char
                self.lines.append(current)
        self.height = len(self.lines) * self.leading + 22
        return self.width, self.height
    def split(self, available_width: float, available_height: float):
        self.wrap(available_width, available_height)
        count = math.floor((available_height - 22) / self.leading)
        if count < 2 or count >= len(self.lines):
            return []
        return [CodeBlock("", self.lines[:count]), CodeBlock("", self.lines[count:])]
    def draw(self):
        canvas = self.canv
        canvas.setFillColor(TINT)
        canvas.setStrokeColor(LINE)
        canvas.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=1)
        canvas.setFont("GuideSC", self.font_size)
        canvas.setFillColor(INK)
        y = self.height - 15
        for line in self.lines:
            canvas.drawString(12, y, line)
            y -= self.leading


def split_cells(line: str) -> list[str]:
    return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def is_table_rule(line: str) -> bool:
    cells = split_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def render_table(rows: list[list[str]], path: Path) -> list[Flowable]:
    count = len(rows[0])
    rows = [row + [""] * (count - len(row)) if len(row) < count else row[:count] for row in rows]
    visible_lengths = [len(re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell)) for row in rows[1:] for cell in row]
    if count >= 7 or (count >= 5 and max(visible_lengths, default=0) > 80):
        # Wide Markdown tables become explicit label/value cards. No cells are
        # omitted, and each original row remains a single inspectable record.
        output: list[Flowable] = []
        headers = rows[0]
        for number, row in enumerate(rows[1:], start=1):
            title = row[0] or f"记录 {number:02d}"
            data = [[paragraph(title, path, "cellhead"), ""]]
            data.extend([paragraph(header, path, "cardlabel"), paragraph(value or " ", path, "cell")] for header, value in zip(headers[1:], row[1:]))
            table = LongTable(data, colWidths=[98, WIDTH - 98], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F3F6F1")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            output.extend([table, Spacer(1, 10)])
        return output
    proportions = {1: [1], 2: [0.29, 0.71], 3: [0.25, 0.36, 0.39], 4: [0.20, 0.27, 0.27, 0.26], 5: [0.19, 0.20, 0.20, 0.22, 0.19], 6: [0.17, 0.16, 0.16, 0.18, 0.17, 0.16]}[count]
    data = [[paragraph(cell or " ", path, "cellhead" if index == 0 else "cell") for cell in row] for index, row in enumerate(rows)]
    table = LongTable(data, colWidths=[WIDTH * fraction for fraction in proportions], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F1F5F0"), PAPER]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, TEAL),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [table, Spacer(1, 10)]


def heading(text: str, level: int, path: Path, first: bool = False) -> Paragraph:
    result = paragraph(text, path, "h1" if first else "h2" if level <= 2 else "h3")
    result._bookmark = file_key(path) if first else file_key(path) + "-" + slug(text)
    result._plain_title = re.sub(r"[`*_]", "", clean(text))
    result._toc_level = 0 if first else None
    return result


def markdown(text: str, path: Path) -> list[Flowable]:
    lines = text.splitlines()
    output: list[Flowable] = []
    index = 0
    first_heading = True
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            if language == "mermaid":
                output.append(paragraph("路线关系请见本册的矢量岗位路线图；源文件保留可编辑 Mermaid。", path, "small"))
            else:
                output.extend([CodeBlock("\n".join(block)), Spacer(1, 10)])
                if any(pdfmetrics.stringWidth(clean(source_line).expandtabs(4), "GuideSC", 8.6) > WIDTH - 24 for source_line in block):
                    source_path = path.relative_to(ROOT).as_posix()
                    BUNDLE_PATHS.add(source_path)
                    output.append(paragraph(f"长行仅为排版折行。复制执行或复制输入时，请从源码 ZIP 解压后打开完整原文。源码包内：`{source_path}`。", path, "caption"))
            index += 1
            continue
        if index + 1 < len(lines) and "|" in line and is_table_rule(lines[index + 1]):
            rows = [split_cells(line)]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(split_cells(lines[index]))
                index += 1
            output.extend(render_table(rows, path))
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            output.append(heading(match.group(2), len(match.group(1)), path, first_heading))
            if first_heading:
                output.append(Rule(space=10))
            first_heading = False
            index += 1
            continue
        if re.fullmatch(r"[-*_]{3,}", line):
            output.append(Rule())
            index += 1
            continue
        match = re.match(r"^(?:[-*+]\s+|([0-9]+)[.)]\s+)(.*)$", line)
        if match:
            prefix = (match.group(1) + ". ") if match.group(1) else "• "
            output.append(paragraph(prefix + match.group(2), path, "bullet"))
            index += 1
            continue
        if line.startswith(">"):
            quote = line.lstrip("> ")
            table = LongTable([[paragraph(quote, path)]], colWidths=[WIDTH])
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("LINEBEFORE", (0, 0), (0, -1), 2.5, TEAL), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
            output.extend([table, Spacer(1, 8)])
            index += 1
            continue
        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or re.match(r"^(#|```|>|[-*+]\s|\d+[.)]\s)", candidate):
                break
            if index + 1 < len(lines) and "|" in candidate and is_table_rule(lines[index + 1]):
                break
            paragraph_lines.append(candidate)
            index += 1
        output.append(paragraph(" ".join(paragraph_lines), path))
    return output


class RoleMap(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 344
    def draw(self):
        canvas = self.canv
        rows = [
            ("新方法 / 新实验结论", "R1 · 研究型算法", "研究问题、相关工作、对照实验、本人贡献"),
            ("预测 / 排序 / 推荐", "R1 · 应用机器学习", "数据划分、基线、指标、失败分析"),
            ("可靠的模型系统", "R2 · AI 工程", "接口、产物、测量、监控、回滚"),
            ("可用的 AI 功能", "R3 · AI 应用工程", "检索、评测、权限、引用、拒答"),
        ]
        x_positions = (0, 151, 310)
        widths = (130, 138, WIDTH - 310)
        for index, label in enumerate(("岗位的主要产出", "优先研究的路线", "用什么证明")):
            canvas.setFillColor(MUTED)
            canvas.setFont("GuideSC-Bold", 9.5)
            canvas.drawString(x_positions[index], 326, label)
        for row_index, values in enumerate(rows):
            y = 247 - row_index * 77
            for col, value in enumerate(values):
                canvas.setFillColor(TEAL if col == 1 else TINT)
                canvas.roundRect(x_positions[col], y, widths[col], 60, 5, fill=1, stroke=0)
                p = Paragraph(html.escape(value), ParagraphStyle("Map", fontName="GuideSC-Bold" if col == 1 else "GuideSC", fontSize=10.0, leading=15, textColor=colors.white if col == 1 else INK, wordWrap="CJK"))
                _, height = p.wrap(widths[col] - 18, 50)
                p.drawOn(canvas, x_positions[col] + 9, y + (60 - height) / 2)
                if col < 2:
                    arrow_x = x_positions[col] + widths[col] + 4
                    canvas.setStrokeColor(TEAL)
                    canvas.setLineWidth(1)
                    canvas.line(arrow_x, y + 30, arrow_x + 12, y + 30)
                    canvas.line(arrow_x + 12, y + 30, arrow_x + 8, y + 33)
                    canvas.line(arrow_x + 12, y + 30, arrow_x + 8, y + 27)


def draw_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)
    canvas.setFont("GuideSC-Bold", 12)
    canvas.drawString(LEFT, PAGE_H - 62, "AI 酋长 Andy")
    canvas.setFont("GuideSC", 9)
    canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 62, "OPEN SOURCE · 2026.11")
    canvas.setStrokeColor(LINE)
    canvas.line(LEFT, PAGE_H - 79, PAGE_W - RIGHT, PAGE_H - 79)
    canvas.setFillColor(MUTED)
    canvas.setFont("GuideSC", 18)
    canvas.drawString(LEFT, PAGE_H - 151, "中国留学生")
    canvas.setFillColor(INK)
    canvas.setFont("GuideSC-Bold", 38)
    canvas.drawString(LEFT, PAGE_H - 212, "AI 岗位求职")
    canvas.setFont("GuideSC-Bold", 30)
    canvas.drawString(LEFT, PAGE_H - 261, "保姆级攻略")
    canvas.setFillColor(TEAL)
    canvas.setFont("GuideSC", 13)
    canvas.drawString(LEFT, PAGE_H - 310, "岗位判断 · 能力差距 · 可验证项目 · 技术面试")
    canvas.setFillColor(MUTED)
    canvas.setFont("GuideSC", 10.3)
    canvas.drawString(LEFT, PAGE_H - 344, "面向不同学历、专业与技术起点的中国留学生")
    canvas.drawString(LEFT, PAGE_H - 363, "北美 / 欧洲 / 亚洲 / 大洋洲 / 回国求职")
    # Accurate, restrained vector motif: three independent routes share an
    # evidence ledger, rather than suggesting one route fits every candidate.
    y = 385
    for i, (code, name) in enumerate((("R1", "算法与机器学习"), ("R2", "AI 工程"), ("R3", "AI 应用工程"))):
        x = LEFT + i * 168
        canvas.setFillColor(TINT)
        canvas.roundRect(x, y, 152, 71, 5, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.setFont("GuideSC-Bold", 17)
        canvas.drawString(x + 13, y + 42, code)
        canvas.setFillColor(INK)
        canvas.setFont("GuideSC", 10.3)
        canvas.drawString(x + 13, y + 18, name)
    canvas.setFillColor(INK)
    canvas.rect(0, 0, PAGE_W, 323, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#B9DBCC"))
    canvas.setFont("GuideSC-Bold", 10)
    canvas.drawString(LEFT, 281, "完整中文攻略  +  可运行样例  +  可编辑模板")
    canvas.setFillColor(colors.white)
    canvas.setFont("GuideSC", 12)
    canvas.drawString(LEFT, 245, "先读懂岗位，再建立经得起追问的证据。")
    canvas.setFont("GuideSC", 10)
    for index, line in enumerate(("作者：AI 酋长 Andy", "微信：AIPMAndy   /   公众号：AI酋长Andy", "个人官网：https://metaver.vip/", "公司官网：https://www.a6no1.cn/")):
        canvas.drawString(LEFT, 198 - index * 23, line)
    canvas.linkURL("https://metaver.vip/", (LEFT, 145, LEFT + 280, 162), relative=0)
    canvas.linkURL("https://www.a6no1.cn/", (LEFT, 122, LEFT + 290, 139), relative=0)
    canvas.setStrokeColor(colors.HexColor("#46564D"))
    canvas.line(LEFT, 77, PAGE_W - RIGHT, 77)
    canvas.setFillColor(colors.HexColor("#B8C7BE"))
    canvas.setFont("GuideSC", 8.4)
    canvas.drawString(LEFT, 52, "版本 2026-11-13 · 免费完整开放 · 教学案例明确标注 · 不承诺 Offer")
    canvas.restoreState()


def draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("GuideSC", 8)
    canvas.drawString(LEFT, PAGE_H - 29, "中国留学生 AI 岗位求职保姆级攻略")
    canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 29, "2026-11-13")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(LEFT, PAGE_H - 39, PAGE_W - RIGHT, PAGE_H - 39)
    canvas.line(LEFT, 37, PAGE_W - RIGHT, 37)
    canvas.setFont("GuideSC", 7.8)
    canvas.drawString(LEFT, 23, "AI 酋长 Andy  ·  微信 AIPMAndy")
    canvas.setFillColor(TEAL)
    canvas.setFont("GuideSC-Bold", 9)
    canvas.drawRightString(PAGE_W - RIGHT, 22, f"{doc.page:02d}")
    canvas.restoreState()


class GuideDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
                         topMargin=TOP, bottomMargin=BOTTOM, title="中国留学生 AI 岗位求职保姆级攻略",
                         author="AI 酋长 Andy", subject="AI岗位判断、能力差距、可验证项目与技术面试",
                         pageCompression=1, allowSplitting=1)
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[Frame(LEFT, BOTTOM, WIDTH, HEIGHT, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=draw_cover),
            PageTemplate(id="Body", frames=[Frame(LEFT, BOTTOM, WIDTH, HEIGHT, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=draw_page),
        ])
        self.bookmarks_seen: set[str] = set()
    def beforeDocument(self):
        self.bookmarks_seen = set()
    def afterFlowable(self, flowable):
        key = getattr(flowable, "_bookmark", None)
        if key and key not in self.bookmarks_seen:
            self.bookmarks_seen.add(key)
            self.canv.bookmarkPage(key)
            if getattr(flowable, "_toc_level", None) is not None:
                title = flowable._plain_title
                self.canv.addOutlineEntry(title, key, level=0, closed=False)
                self.notify("TOCEntry", (0, title, self.page, key))


class GuideCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        kwargs["initialFontName"] = "GuideSC"
        kwargs["initialFontSize"] = 10.2
        super().__init__(*args, **kwargs)


def static_heading(title: str, key: str) -> Paragraph:
    result = Paragraph(html.escape(title), STYLES["h1"])
    result._bookmark, result._plain_title, result._toc_level = key, title, 0
    return result


def screenshot_pages() -> tuple[list[Flowable], list[str]]:
    story: list[Flowable] = []
    included = []
    for file_stem, title, description in (
        ("operation-home", "操作截图｜从网站开始", "真实浏览器截图：站点首页与内容入口。按自己的岗位路线选择正文、项目和模板。"),
        ("operation-results", "操作截图｜核对结果与限制", "真实浏览器截图：项目结果展示。实际执行的逐题记录与失败样本保存在 examples 下的 JSON 报告中。"),
    ):
        path = next((ROOT / "assets" / (file_stem + suffix) for suffix in (".jpg", ".png", ".jpeg") if (ROOT / "assets" / (file_stem + suffix)).is_file()), None)
        if path is None:
            continue
        story.extend([PageBreak(), static_heading(title, "shot-" + path.stem)])
        story.append(paragraph(description, ROOT / "README.md"))
        with PillowImage.open(path) as image:
            width, height = image.size
        scale = min(WIDTH / width, 555 / height)
        story.append(Image(str(path), width=width * scale, height=height * scale, hAlign="CENTER"))
        story.append(paragraph("截图只展示真实界面。没有把示意画面、AI 生成图片或未执行的结果当成操作证据。", ROOT / "README.md", "caption"))
        story.append(Paragraph("跟着这页做", STYLES["h2"]))
        steps = (
            ("先按主要工作产出选择路线，并独立核对学历、毕业时间、地点与工作资格。", "打开对应的完整运行手册，先看输入、运行命令与失败样本，再决定要补什么。", "下载岗位研究和能力差距模板，填入一条真实 JD，给下一步设置可验收的产出。")
            if file_stem == "operation-home" else
            ("先看指标分母：此处是 12 条合成测试工单，不能换成真实业务准确率。", "把模型与多数类基线一起看，再检查各类别表现，避免只挑一个好看的数字。", "读完两条失败，提出一个可被验证的改进假设；保留旧结果，不把已看过的测试集当新证据。")
        )
        for index, step in enumerate(steps, start=1):
            story.append(paragraph(f"{index}. {step}", ROOT / "README.md", "bullet"))
        included.append(str(path.relative_to(ROOT)))
    return story, included


def build_story(files: list[tuple[str, Path]]) -> tuple[list[Flowable], list[str]]:
    story: list[Flowable] = [Spacer(1, 1), NextPageTemplate("Body"), PageBreak()]
    meta = ROOT / "README.md"
    story.append(static_heading("这本手册怎么用", "about-this-guide"))
    story.append(paragraph("先判断目标岗位，再补能力证据。你可以独立使用本册；不需要先读完其他专题。", meta))
    story.append(paragraph("作者：AI 酋长 Andy。前腾讯、百度 AI 产品专家，前大模型公司 VP。提供求职咨询、AI 转型与陪跑服务。", meta))
    story.append(paragraph("版本日期：2026-11-13。岗位与地区规则以各来源的核验状态为准；申请前重新打开原文。公开页面可读，不代表岗位仍有名额或雇主接受每一种身份。", meta))
    story.append(paragraph("本书的三个技术案例全部是教学模拟。代码、输入、评测和失败样本完整开放；不虚构客户、Offer、薪资、成功率或商业成绩。", meta))
    story.append(paragraph("覆盖北美、欧洲、亚洲、大洋洲与中国籍留学生回国场景。对尚未核实的国家、岗位和政策条款，明确列在缺口清单中；不声称穷尽所有地区。非洲、南美洲不在本项目范围。", meta))
    story.extend(render_table([
        ["阅读目标", "从哪里开始"],
        ["还不知道申请什么", "00 快速开始 → 01 岗位路线 → 02 能力差距"],
        ["会一些技术但没有可信作品", "03 经历证据 → 04 技术项目 → 三个完整运行手册"],
        ["准备申请和面试", "05 作品集与简历 → 06 技术面试 → 07 地区资格 → 08 定向申请"],
        ["投了很多却不知道卡在哪里", "09 复盘 → 投递台账、面试清单与失败分析模板"],
    ], meta))
    story.append(paragraph("免费内容完整开放。咨询入口承接岗位判断、项目诊断与求职陪跑，不承诺录用结果。", meta))
    story.append(paragraph("微信：AIPMAndy · 公众号：AI酋长Andy\n个人官网：https://metaver.vip/\n公司官网：https://www.a6no1.cn/", meta))
    story.append(paragraph("解压源码 ZIP 后，按“源码包内”路径打开对应文件。代码许可见 LICENSE-CODE；合成数据许可见 examples/DATA-LICENSE.md。正文与第三方来源按仓库许可说明使用；第三方招聘原文、政策、商标与论文的权利归相应权利人。", meta, "small"))
    story.append(PageBreak())
    story.append(Paragraph("目录", STYLES["h1"]))
    story.append(paragraph("点击章节名称或页码可以跳转；PDF 左侧书签也可导航。", meta, "small"))
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC", fontName="GuideSC", fontSize=10.0, leading=17.5,
                                     textColor=INK, leftIndent=0, firstLineIndent=0, rightIndent=22,
                                     spaceBefore=3, spaceAfter=3, wordWrap="CJK")]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.extend([PageBreak(), static_heading("岗位路线图｜先看主要交付物", "role-map")])
    story.append(paragraph("R1 中的研究与应用机器学习是不同子路径。工作名称相近，也可能要求完全不同的证据。", meta))
    story.append(RoleMap())
    story.append(paragraph("AI 产品经理归产品求职专题；数据科学与解决方案岗位按主体工作分流。主要做建模、编码交付与部署的可落在本册，主要做经营分析、售前或需求优先级的另选专题。", meta))
    story.append(paragraph("先核学历、毕业时间、地点与工作资格；这些条件不能靠“技能匹配总分”互相抵消。再比较职责和证据，决定“可投、先确认、先补、暂不投”。", meta))
    chapter_labels = {"guide": "实操正文", "case": "技术案例总览", "project": "完整运行手册", "research": "事实与来源", "template": "可编辑工作模板"}
    previous_part = None
    for kind, path in files:
        part = "technical" if kind in {"case", "project"} else kind
        if part != previous_part:
            story.append(PageBreak())
        else:
            # A short final note must not leave an almost-empty page. Start the
            # next chapter on that page only when almost two thirds of the
            # usable frame remains; major parts still start on a new page.
            story.extend([CondPageBreak(HEIGHT * 0.64), Spacer(1, 18)])
        story.append(Paragraph(chapter_labels[kind], STYLES["eyebrow"]))
        story.extend(markdown(path.read_text(encoding="utf-8"), path))
        previous_part = part
    shots, included = screenshot_pages()
    story.extend(shots)
    story.extend([PageBreak(), static_heading("完整链接索引", "all-source-links")])
    story.append(paragraph("以下链接由本册源文件自动提取并去重。原始核验日期、访问限制和适用范围见前面的岗位与地区记录。链接可点击，长地址按版面换行。", meta))
    bibliography = [(url, label) for url, label in SOURCE_LINKS.items() if not url.startswith(("https://metaver.vip", "https://www.a6no1.cn"))]
    for index, (url, label) in enumerate(bibliography, start=1):
        story.append(KeepTogether([
            Paragraph(f'<b>{index:03d}</b>  {html.escape(clean(label))}', STYLES["small"]),
            Paragraph(f'<link href="{html.escape(url, quote=True)}" color="#126653">{html.escape(clean(url))}</link>', STYLES["small"]),
            Spacer(1, 4),
        ]))
    story.extend([Spacer(1, 16), Rule(), paragraph("作者：AI 酋长 Andy · 微信：AIPMAndy · 公众号：AI酋长Andy", meta), paragraph("个人官网：https://metaver.vip/ · 公司官网：https://www.a6no1.cn/", meta)])
    return story, included


def inspect_pdf(path: Path, files: list[tuple[str, Path]], screenshots: list[str]) -> dict:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    required = ["中国留学生", "AI 岗位求职", "AI 酋长 Andy", "AIPMAndy", "AI酋长Andy", "metaver.vip", "a6no1.cn"]
    missing = [item for item in required if item not in text]
    if missing:
        raise ValueError(f"PDF text checks failed: {missing}")
    links = 0
    for page in reader.pages:
        links += sum(annotation.get_object().get("/Subtype") == "/Link" for annotation in page.get("/Annots", []))
    report = {"version": VERSION, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "pdf": str(path.relative_to(ROOT)), "pages": len(reader.pages), "bytes": path.stat().st_size,
              "source_files": [str(p.relative_to(ROOT)) for _, p in files], "source_file_count": len(files),
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for _, p in files},
              "screenshots_included": screenshots, "screenshot_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in screenshots}, "link_annotations": links, "text_characters": len(text),
              "brand_text_check": "passed", "visual_review": "pending; inspect rendered pages before release"}
    missing_bundle_paths = [name for name in BUNDLE_PATHS if not (ROOT / name).is_file()]
    if missing_bundle_paths:
        raise FileNotFoundError("PDF source bundle targets are missing: " + ", ".join(sorted(missing_bundle_paths)))
    report["source_bundle_path_count"] = len(BUNDLE_PATHS)
    report["generated_external_source_link_count"] = 0
    (PDF_DIR / "source-links.json").write_text(json.dumps({
        "strategy": "Included chapters use internal PDF destinations; other relative source targets are readable paths inside the supplied source ZIP. No unpublished repository or website URLs are generated.",
        "external_source_urls": [], "pending_source_http_checks": 0,
        "bundle_paths": sorted(BUNDLE_PATHS), "local_source_files": "all present",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PDF_DIR / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def render_pdf(path: Path) -> dict:
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm is required for --render; install Poppler")
    directory = ROOT / "tmp/pdf-pages"
    directory.mkdir(parents=True, exist_ok=True)
    for previous in directory.glob("*.png"):
        previous.unlink()
    subprocess.run(["pdftoppm", "-r", "65", "-png", str(path), str(directory / "page")], check=True)
    pages = sorted(directory.glob("page-*.png"))
    contact_dir = ROOT / "tmp/pdf-contact-sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)
    for previous in contact_dir.glob("*.jpg"):
        previous.unlink()
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    sheets = []
    for start in range(0, len(pages), 6):
        group = pages[start:start + 6]
        sheet = PillowImage.new("RGB", (1240, 1780), "#DDE2DB")
        draw = ImageDraw.Draw(sheet)
        for index, page in enumerate(group):
            image = PillowImage.open(page).convert("RGB")
            image.thumbnail((580, 535))
            x = 30 + (index % 2) * 610 + (580 - image.width) // 2
            y = 28 + (index // 2) * 585
            sheet.paste(image, (x, y))
            draw.text((x, y + image.height + 5), f"PAGE {start + index + 1:03d}", fill="#163C31", font=font)
        target = contact_dir / f"contact-{start + 1:03d}-{start + len(group):03d}.jpg"
        sheet.save(target, quality=88)
        sheets.append(str(target.relative_to(ROOT)))
    return {"rendered_pages": len(pages), "contact_sheets": sheets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PDF_DIR / "chinese-international-student-ai-jobs-guide.pdf")
    parser.add_argument("--font-regular", default="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    parser.add_argument("--font-bold", default="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
    parser.add_argument("--font-number", type=int, default=2, help="Noto CJK TTC index 2 is Simplified Chinese")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    files = source_files()
    if len(files) < 18:
        raise RuntimeError("Too few source files: ensure docs, research and examples are complete")
    SOURCE_MAP.update({path.resolve(): file_key(path) for _, path in files})
    register_fonts(files, args)
    story, screenshots = build_story(files)
    doc = GuideDoc(str(args.output))
    doc.multiBuild(story, canvasmaker=GuideCanvas)
    report = inspect_pdf(args.output, files, screenshots)
    if args.render:
        report.update(render_pdf(args.output))
        (PDF_DIR / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("pdf", "pages", "bytes", "source_file_count", "screenshots_included", "link_annotations")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
