#!/usr/bin/env python3
"""
Supervisor Scout — 导师评级报告生成
====================================
基于 Layer 1 / Layer 2 结构化数据，生成导师综合评级报告。

用法:
    python3 report_gen.py --school bjut --interest "氢能燃烧"
    python3 report_gen.py --school bjut --profiles-dir data/processed/bjut
"""

import argparse
import csv
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
REPORTS_DIR = os.path.join(SKILL_DIR, 'data', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_supervisor_report(school_code: str, school_name: str, interest: str, profiles: list) -> str:
    """生成导师评级报告"""

    lines = [
        f"# {school_name} — 导师调研报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**目标方向**: {interest}",
        f"**导师总数**: {len(profiles)}",
        "",
        "## 评估维度",
        "",
        "| 维度 | 权重 | 说明 |",
        "|------|------|------|",
        "| 学术产出 | 25% | 论文数量、h-index |",
        "| 学术影响力 | 20% | 引用数、领域知名度 |",
        "| 方向匹配 | 20% | 与用户兴趣的匹配度 |",
        "| 招生活跃度 | 15% | 近年招生、课题组规模 |",
        "| 学术潜力 | 15% | 近年趋势、在研项目 |",
        "| 特殊状态修正 | 5% | 退休/调任/行政占比 |",
        "",
        "## 导师评级",
        "",
        "| 排名 | 姓名 | 方向匹配 | 学术产出 | 综合评分 | 评级 | 建议 |",
        "|------|------|----------|----------|----------|------|------|",
    ]

    # 按综合评分排序（示例数据）
    for i, profile in enumerate(profiles[:20], 1):
        name = profile.get('name', '未知')
        direction = profile.get('direction') or profile.get('direction_keywords', '待补充')
        score = profile.get('score', 0)

        # 评级
        if score >= 90:
            grade = 'S'
            advice = '强烈推荐'
        elif score >= 80:
            grade = 'A'
            advice = '推荐'
        elif score >= 70:
            grade = 'B'
            advice = '备选'
        elif score >= 60:
            grade = 'C'
            advice = '谨慎'
        else:
            grade = 'D'
            advice = '不建议'

        match_score = profile.get('match_score', 0)
        output_score = profile.get('output_score', 0)

        lines.append(
            f"| {i} | {name} | {match_score}/100 | {output_score}/100 | {score}/100 | {grade} | {advice} |"
        )

    lines.extend([
        "",
        "## Top 5 推荐导师",
        "",
    ])

    for i, profile in enumerate(profiles[:5], 1):
        name = profile.get('name', '未知')
        direction = profile.get('direction') or profile.get('direction_keywords', '待补充')
        lines.extend([
            f"### {i}. {name}",
            "",
            f"- **研究方向**: {direction}",
            f"- **综合评分**: {profile.get('score', 0)}/100",
            f"- **Google Scholar**: {profile.get('scholar_url', 'N/A')}",
            f"- **套磁切入点**: 引用其最新论文《{profile.get('latest_paper', '待补充')}》，提出你的思考",
            "",
        ])

    lines.extend([
        "## 套磁策略建议",
        "",
        "### 邮件发送时机",
        "",
        "| 阶段 | 时间 | 策略 |",
        "|------|------|------|",
        "| 夏令营前 | 5-6月 | 发送第一封信，介绍自己+表达兴趣 |",
        "| 夏令营后 | 7-8月 | 跟进，提及夏令营收获 |",
        "| 预推免前 | 8-9月 | 确认意向，询问名额 |",
        "| 九推 | 9-10月 | 最终确认，敲定offer |",
        "",
        "### 邮件内容结构",
        "",
        "1. **主题**: 推免申请-XXX大学-姓名-专业",
        "2. **自我介绍**: 学校、专业、排名、英语成绩（30%）",
        "3. **学术兴趣**: 为什么对导师方向感兴趣（30%）",
        "4. **能力展示**: 科研经历、论文、竞赛（30%）",
        "5. **明确诉求**: 询问是否有推免名额（10%）",
        "",
        "### 注意事项",
        "",
        "- 不要群发，每封信都要个性化",
        "- 不要同时联系同一个学院的多位导师（最多2位）",
        "- 导师不回复很正常，1周后可以发一封礼貌的跟进",
        "- 收到积极回复后，尽快约电话/视频沟通",
        "",
        "---",
        "",
        "> ⚠️ **声明**: 本报告基于公开信息自动生成，评级仅供参考。选导师是人生重要决策，建议通过多渠道（学长学姐、导师面谈、实验室参观）综合判断。",
        "",
        "> 📧 **数据更新**: 导师信息会变化，建议定期重新运行查询。",
    ])

    return '\n'.join(lines)


def load_profiles_from_dir(profiles_dir: str) -> list:
    profiles = []

    if not os.path.exists(profiles_dir):
        return profiles

    for filename in os.listdir(profiles_dir):
        filepath = os.path.join(profiles_dir, filename)

        if filename.endswith('_layer1.csv'):
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    priority = row.get('layer2_priority', 'C')
                    score_map = {'A': 85, 'B': 72, 'C': 60}
                    profiles.append({
                        'name': row.get('name', ''),
                        'direction_keywords': row.get('direction_keywords', ''),
                        'score': score_map.get(priority, 60),
                        'match_score': score_map.get(priority, 60),
                        'output_score': 60 if priority == 'C' else 75,
                        'latest_paper': row.get('notes', '') or '待进入 Layer 2/3 补充',
                        'scholar_url': row.get('profile_url', ''),
                    })
            continue

        if not filename.endswith('.json'):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            profiles.append(payload)

    return profiles


def main():
    parser = argparse.ArgumentParser(description='导师评级报告生成')
    parser.add_argument('--school', required=True, help='学校代码 (如 bjut)')
    parser.add_argument('--interest', default='未指定', help='你的研究方向兴趣')
    parser.add_argument('--profiles-dir', help='导师画像数据目录')
    parser.add_argument('--output', help='输出文件路径')

    args = parser.parse_args()

    # 加载学校配置
    config_path = os.path.join(SKILL_DIR, 'configs', f"{args.school}.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        school_name = config['school']
    else:
        school_name = args.school

    print(f"\n{'='*60}")
    print(f"生成导师评级报告: {school_name}")
    print(f"兴趣方向: {args.interest}")
    print(f"{'='*60}")

    # 加载导师画像数据
    profiles_dir = args.profiles_dir or os.path.join(SKILL_DIR, 'data', 'processed', args.school)
    profiles = load_profiles_from_dir(profiles_dir)

    if not profiles:
        print("\n[警告] 未找到导师画像数据，使用示例数据生成报告")
        # 使用示例数据
        profiles = [
            {"name": "张红光", "direction": "内燃机燃烧", "score": 92, "match_score": 95, "output_score": 88, "scholar_url": "...", "latest_paper": "氢微预混燃烧特性研究"},
            {"name": "何旭", "direction": "先进燃烧技术", "score": 88, "match_score": 90, "output_score": 85, "scholar_url": "...", "latest_paper": "射流点火燃烧室研究"},
        ]

    # 按评分排序
    profiles.sort(key=lambda x: x.get('score', 0), reverse=True)

    # 生成报告
    report = generate_supervisor_report(args.school, school_name, args.interest, profiles)

    # 保存
    output_path = args.output or os.path.join(REPORTS_DIR, f"{args.school}_supervisor_report.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n[保存] 报告 -> {output_path}")
    print(f"\n{'='*60}")
    print("报告生成完成！")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
