from __future__ import annotations

import copy
import re
from typing import Any


FONT_NAMES = ["宋体", "仿宋", "楷体", "黑体"]
SIZE_NAMES = ["小五", "五号", "小四", "四号", "小三"]


def _ensure_path(root: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    current = root
    for key in keys:
        current = current.setdefault(key, {})
    return current


def _extract_field_text(text: str, label: str) -> str | None:
    match = re.search(rf"{label}[：:]\s*([^\n，。]+)", text)
    return match.group(1).strip() if match else None


def _contains_any(text: str, tokens: list[str]) -> str | None:
    for token in tokens:
        if token in text:
            return token
    return None


def _match_numeric(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def apply_rule_overrides(base_rules: dict[str, Any], instruction: str) -> tuple[dict[str, Any], list[str]]:
    rules = copy.deepcopy(base_rules)
    notes: list[str] = []
    text = (instruction or "").strip()
    if not text:
        return rules, notes

    typography = _ensure_path(rules, ["typography"])
    paragraph = _ensure_path(rules, ["paragraph"])
    page = _ensure_path(rules, ["page"])
    headings = _ensure_path(rules, ["headings"])

    if "总标题黑体小二" in text or "标题黑体小二" in text or "标题黑体 小二" in text:
        typography["title_font"] = "黑体"
        typography["title_size"] = "小二"
        typography["title_weight"] = "bold"
        notes.append("总标题改为黑体小二")

    # 正文字体 / 字号只在“正文”明确出现时覆盖，避免被页眉页脚串改
    body_font_match = re.search(r"正文(?:字体)?(仿宋\s*GB2312|宋体|仿宋|楷体|黑体)", text)
    if body_font_match:
        typography["body_font"] = body_font_match.group(1).replace(" ", "")
        notes.append(f"正文改为{body_font_match.group(1).replace(' ', '')}")
    elif not any(scope in text for scope in ["页眉", "页脚", "页码"]):
        standalone_font = _contains_any(text, FONT_NAMES)
        if standalone_font:
            typography["body_font"] = standalone_font
            notes.append(f"正文改为{standalone_font}")

    body_size_match = re.search(r"正文(?:字号)?(小五|五号|小四|四号|小三)", text)
    if body_size_match:
        typography["body_size"] = body_size_match.group(1)
        notes.append(f"正文字号改为{body_size_match.group(1)}")
    elif not any(scope in text for scope in ["页眉", "页脚", "页码"]):
        standalone_size = _contains_any(text, SIZE_NAMES)
        if standalone_size:
            typography["body_size"] = standalone_size
            notes.append(f"正文字号改为{standalone_size}")

    if "一级标题跟正文" in text or "一级标题依赖正文" in text:
        typography["heading_font"] = typography.get("body_font", "仿宋 GB2312")
        notes.append("一级标题字体跟随正文")
    if "二级标题跟正文" in text or "二级标题依赖正文" in text:
        typography["heading_font"] = typography.get("body_font", "仿宋 GB2312")
        notes.append("二级标题字体跟随正文")
    if "一级标题依赖正文" in text or "二级标题依赖正文" in text:
        typography["heading_font"] = typography.get("body_font", "仿宋 GB2312")
        notes.append("标题字体统一跟随正文")
    if "标题加粗" in text or "一级标题加粗" in text or "二级标题加粗" in text:
        typography["heading_weight"] = "bold"
        notes.append("标题改为加粗")
    if "标题不加粗" in text or "标题取消加粗" in text:
        typography["heading_weight"] = "normal"
        notes.append("标题取消加粗")

    if "固定28磅" in text or "28磅" in text:
        paragraph["line_spacing"] = "28"
        notes.append("行距改为固定28磅")
    else:
        line_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*倍行距", text)
        if line_match:
            paragraph["line_spacing"] = line_match.group(1)
            notes.append(f"行距改为{line_match.group(1)} 倍")
        elif "单倍行距" in text:
            paragraph["line_spacing"] = "1"
            notes.append("行距改为单倍")
        elif "1.5倍行距" in text or "1.5 倍行距" in text:
            paragraph["line_spacing"] = "1.5"
            notes.append("行距改为1.5倍")
        elif "2倍行距" in text or "2 倍行距" in text:
            paragraph["line_spacing"] = "2"
            notes.append("行距改为2倍")

    heading_size_patterns = [
        (r"一级标题字号(?:为|是|改为)?\s*(三号|小三|四号|小四|小五|\d+(?:\.\d+)?)", "heading1_size", "一级标题字号"),
        (r"二级标题字号(?:为|是|改为)?\s*(三号|小三|四号|小四|小五|\d+(?:\.\d+)?)", "heading2_size", "二级标题字号"),
        (r"三级标题字号(?:为|是|改为)?\s*(三号|小三|四号|小四|小五|\d+(?:\.\d+)?)", "heading3_size", "三级标题字号"),
    ]
    for pattern, key, label in heading_size_patterns:
        match = re.search(pattern, text)
        if match:
            typography[key] = match.group(1)
            notes.append(f"{label}改为{match.group(1)}磅")

    if "首行缩进两字符" in text or "首行缩进2字符" in text:
        paragraph["first_line_indent"] = "2char"
        notes.append("首行缩进改为两字符")
    elif "首行缩进一字符" in text or "首行缩进1字符" in text:
        paragraph["first_line_indent"] = "1char"
        notes.append("首行缩进改为一字符")
    elif "不缩进" in text or "首行不缩进" in text:
        paragraph["first_line_indent"] = "0"
        notes.append("首行缩进取消")
    elif "悬挂缩进" in text:
        paragraph["first_line_indent"] = "hanging"
        notes.append("首行缩进改为悬挂缩进")

    spacing_after_match = re.search(r"段后\s*([0-9]+(?:\.[0-9]+)?)\s*磅", text)
    if spacing_after_match:
        paragraph["spacing_after"] = spacing_after_match.group(1)
        notes.append(f"段后改为{spacing_after_match.group(1)}磅")
    elif "段后0磅" in text or "段后零磅" in text:
        paragraph["spacing_after"] = "0"
        notes.append("段后改为0磅")

    spacing_before_match = re.search(r"段前\s*([0-9]+(?:\.[0-9]+)?)\s*磅", text)
    if spacing_before_match:
        paragraph["spacing_before"] = spacing_before_match.group(1)
        notes.append(f"段前改为{spacing_before_match.group(1)}磅")
    elif "段前0磅" in text or "段前零磅" in text:
        paragraph["spacing_before"] = "0"
        notes.append("段前改为0磅")

    if "正文两端对齐" in text:
        paragraph["alignment"] = "justify"
        notes.append("正文改为两端对齐")
    elif "正文左对齐" in text:
        paragraph["alignment"] = "left"
        notes.append("正文改为左对齐")
    elif "正文居中" in text:
        paragraph["alignment"] = "center"
        notes.append("正文改为居中")

    heading_spacing_patterns = [
        (r"一级标题段前\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading1_spacing_before", "一级标题段前"),
        (r"一级标题段后\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading1_spacing_after", "一级标题段后"),
        (r"二级标题段前\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading2_spacing_before", "二级标题段前"),
        (r"二级标题段后\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading2_spacing_after", "二级标题段后"),
        (r"三级标题段前\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading3_spacing_before", "三级标题段前"),
        (r"三级标题段后\s*([0-9]+(?:\.[0-9]+)?)\s*磅", "heading3_spacing_after", "三级标题段后"),
    ]
    for pattern, key, label in heading_spacing_patterns:
        match = re.search(pattern, text)
        if match:
            headings[key] = match.group(1)
            notes.append(f"{label}改为{match.group(1)}磅")

    if "标题居中" in text:
        headings["heading_align"] = "center"
        notes.append("标题改为居中")
    elif "标题左对齐" in text:
        headings["heading_align"] = "left"
        notes.append("标题改为左对齐")

    if "窄页边距" in text:
        page["margin"] = "narrow"
        notes.append("页边距改为窄")
    elif "宽页边距" in text:
        page["margin"] = "wide"
        notes.append("页边距改为宽")
    elif "普通页边距" in text or "标准页边距" in text:
        page["margin"] = "normal"
        notes.append("页边距改为普通")

    if "页码启用" in text or "加页码" in text or "显示页码" in text:
        page["page_number"] = "on"
        notes.append("页码改为显示")
    elif "不加页码" in text or "取消页码" in text or "不要页码" in text:
        page["page_number"] = "off"
        notes.append("页码改为不显示")

    if "首页不显示页码" in text or "封面不显示页码" in text:
        page["first_page_number"] = "off"
        notes.append("首页页码改为不显示")
    elif "首页显示页码" in text or "封面显示页码" in text:
        page["first_page_number"] = "on"
        notes.append("首页页码改为显示")

    if "页码居中" in text:
        page["page_number_align"] = "center"
        notes.append("页码改为居中")
    elif "页码右对齐" in text or "页码居右" in text:
        page["page_number_align"] = "right"
        notes.append("页码改为右对齐")
    elif "页码左对齐" in text or "页码居左" in text:
        page["page_number_align"] = "left"
        notes.append("页码改为左对齐")

    for label, font_key, size_key in [
        ("页眉", "header_font", "header_size"),
        ("页脚", "footer_font", "footer_size"),
        ("页码", "page_number_font", "page_number_size"),
    ]:
        scoped_font = re.search(rf"{label}(?:字体)?(宋体|仿宋|楷体|黑体)", text)
        if scoped_font:
            page[font_key] = scoped_font.group(1)
            notes.append(f"{label}字体改为{scoped_font.group(1)}")
        scoped_size = re.search(rf"{label}(?:字号)?(小五|五号|小四|四号|小三)", text)
        if scoped_size:
            page[size_key] = scoped_size.group(1)
            notes.append(f"{label}字号改为{scoped_size.group(1)}")

    header_text = _extract_field_text(text, "页眉")
    if header_text:
        page["header_text"] = header_text
        notes.append(f"页眉文字改为“{header_text}”")

    footer_text = _extract_field_text(text, "页脚")
    if footer_text:
        page["footer_text"] = footer_text
        notes.append(f"页脚文字改为“{footer_text}”")

    if "页眉居中" in text:
        page["header_align"] = "center"
        notes.append("页眉改为居中")
    elif "页眉右对齐" in text or "页眉居右" in text:
        page["header_align"] = "right"
        notes.append("页眉改为右对齐")
    elif "页眉左对齐" in text or "页眉居左" in text:
        page["header_align"] = "left"
        notes.append("页眉改为左对齐")

    if "页脚居中" in text:
        page["footer_align"] = "center"
        notes.append("页脚改为居中")
    elif "页脚右对齐" in text or "页脚居右" in text:
        page["footer_align"] = "right"
        notes.append("页脚改为右对齐")
    elif "页脚左对齐" in text or "页脚居左" in text:
        page["footer_align"] = "left"
        notes.append("页脚改为左对齐")

    margin_match = re.search(r"(上|下|左|右)(?:边距|页边距)\s*([0-9]+(?:\.[0-9]+)?)\s*cm", text)
    if margin_match:
        side = margin_match.group(1)
        value = margin_match.group(2)
        side_key_map = {"上": "top_margin", "下": "bottom_margin", "左": "left_margin", "右": "right_margin"}
        page[side_key_map[side]] = value
        notes.append(f"{side}边距改为{value}cm")

    return rules, notes
