#!/usr/bin/env python3
"""
Supervisor Scout — Layer 1 批量快筛
====================================
从导师名单生成第一层快筛表，用于海选和后续 Layer 2 分流。
"""

import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

SPECIAL_STATUS_RULES = [
    (['院士'], '院士'),
    (['书记'], '行政/调任风险'),
    (['副院长', '院长', '所长', '主任'], '行政职务'),
    (['校外兼职导师'], '校外兼职导师'),
]

INACTIVE_HINTS = ['中级及其他教工人员']


def load_supervisors(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"输入文件不是导师列表: {path}")
    return data


def infer_research_institute(category: str) -> str:
    return category.split(' | ')[0].strip() if category else ''


def infer_title_rank(category: str) -> str:
    if ' | ' not in category:
        return ''
    return category.split(' | ', 1)[1].strip()


def infer_direction_keywords(institute: str) -> str:
    mappings = {
        '电动车辆工程技术中心': '电动车辆;电池;能量管理',
        '智能车辆研究所': '智能车辆;自动驾驶;感知控制',
        '特种车辆研究所': '特种车辆;越野机动;装备车辆',
        '振动与声学研究所': '振动噪声;NVH;结构动力学',
        '发动机研究所': '发动机;燃烧;排放控制',
        '新能源汽车国家监测与管理平台': '车联网;监测平台;大数据',
    }
    return mappings.get(institute, institute or '待人工补充')


def infer_special_status(supervisor: Dict) -> str:
    text = ' '.join([
        supervisor.get('name', ''),
        supervisor.get('category', ''),
        supervisor.get('college', ''),
    ])
    tags = []
    for keywords, label in SPECIAL_STATUS_RULES:
        if any(keyword in text for keyword in keywords):
            tags.append(label)
    return '；'.join(tags)


def infer_activity_level(category: str) -> str:
    if any(hint in category for hint in INACTIVE_HINTS):
        return '低'
    if '正高级职称' in category:
        return '高'
    if '副高级职称' in category:
        return '中'
    return '中'


def infer_layer2_priority(supervisor: Dict) -> str:
    category = supervisor.get('category', '')
    special_status = infer_special_status(supervisor)
    name = supervisor.get('name', '')

    if '院士' in special_status:
        return 'A'
    if special_status:
        return 'B'
    if any(token in name for token in ['孙逢春', '熊瑞', '何洪文']):
        return 'A'
    if '正高级职称' in category:
        return 'A'
    if '副高级职称' in category:
        return 'B'
    return 'C'


def build_layer1_rows(supervisors: List[Dict]) -> List[Dict]:
    rows = []
    for supervisor in supervisors:
        category = supervisor.get('category', '')
        institute = infer_research_institute(category)
        title_rank = infer_title_rank(category)
        rows.append({
            'name': supervisor.get('name', ''),
            'college': supervisor.get('college', ''),
            'research_institute': institute,
            'title_rank': title_rank,
            'profile_url': supervisor.get('profile_url', ''),
            'paper_signal': '',
            'h_index_signal': '',
            'activity_2025': infer_activity_level(category),
            'direction_keywords': infer_direction_keywords(institute),
            'special_status': infer_special_status(supervisor),
            'layer2_priority': infer_layer2_priority(supervisor),
            'notes': '',
        })
    return rows


def save_csv(rows: List[Dict], path: str):
    fieldnames = [
        'name', 'college', 'research_institute', 'title_rank', 'profile_url',
        'paper_signal', 'h_index_signal', 'activity_2025', 'direction_keywords',
        'special_status', 'layer2_priority', 'notes',
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_markdown(rows: List[Dict], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    priority_counts = Counter(row['layer2_priority'] for row in rows)
    lines = [
        "# Layer 1 快筛结果",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**导师总数**: {len(rows)}",
        f"**A/B/C 分布**: A={priority_counts.get('A', 0)} / B={priority_counts.get('B', 0)} / C={priority_counts.get('C', 0)}",
        "",
        "| 姓名 | 研究所 | 职称 | 2025活跃度 | 方向关键词 | 特殊状态 | Layer 2推荐 |",
        "|------|--------|------|------------|------------|----------|--------------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['research_institute']} | {row['title_rank']} | "
            f"{row['activity_2025']} | {row['direction_keywords']} | "
            f"{row['special_status'] or '-'} | {row['layer2_priority']} |"
        )

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Layer 1 批量快筛')
    parser.add_argument('--input', required=True, help='导师名单 JSON 文件')
    parser.add_argument('--output-csv', help='输出 CSV 路径')
    parser.add_argument('--output-md', help='输出 Markdown 路径')
    args = parser.parse_args()

    supervisors = load_supervisors(args.input)
    rows = build_layer1_rows(supervisors)

    output_csv = args.output_csv or re.sub(r'\.json$', '_layer1.csv', args.input)
    output_md = args.output_md or re.sub(r'\.json$', '_layer1.md', args.input)

    save_csv(rows, output_csv)
    save_markdown(rows, output_md)

    print(f"[保存] CSV -> {output_csv} ({len(rows)} 条)")
    print(f"[保存] Markdown -> {output_md}")


if __name__ == '__main__':
    main()
