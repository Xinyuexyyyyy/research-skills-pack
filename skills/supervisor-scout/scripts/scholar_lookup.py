#!/usr/bin/env python3
"""
Supervisor Scout — 导师学术信息查询
====================================
通过 Google Scholar / ResearchGate / 知网 等渠道查询导师学术信息。

用法:
    python3 scholar_lookup.py --name "张红光" --school "北京工业大学"
    python3 scholar_lookup.py --name "张三" --search-all
    python3 scholar_lookup.py --file mentors.json --batch
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SKILL_DIR, 'data', 'processed')
os.makedirs(DATA_DIR, exist_ok=True)

# Google Scholar 镜像（国内可用）
SCHOLAR_MIRRORS = [
    "https://scholar.google.com",
    "https://scholar.lanfanshu.cn",
    "https://scholar.hhu.edu.cn",
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def get_proxies() -> dict:
    """从环境变量读取代理配置"""
    proxies = {}
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if http_proxy:
        proxies['http'] = http_proxy
    if https_proxy:
        proxies['https'] = https_proxy
    return proxies if proxies else None


def search_google_scholar(name: str, school: str = None) -> dict:
    """
    查询 Google Scholar 导师信息

    注意: Google Scholar 有反爬机制，频繁请求会被封IP。
    建议通过代理访问或使用学术镜像站。

    代理配置:
        export HTTP_PROXY=http://127.0.0.1:7890
        export HTTPS_PROXY=http://127.0.0.1:7890
    """
    proxies = get_proxies()
    query = f'"{name}"'
    if school:
        query += f' {school}'

    # 尝试多个镜像
    for mirror in SCHOLAR_MIRRORS:
        try:
            url = f"{mirror}/scholar?q={quote(query)}"
            response = requests.get(url, headers=HEADERS, timeout=15, proxies=proxies)
            if response.status_code == 200:
                return _parse_scholar_profile(response.text, name)
        except Exception as e:
            print(f"  [警告] {mirror} 访问失败: {e}")
            continue
        time.sleep(1)

    return {"status": "failed", "reason": "所有镜像均无法访问"}


def _parse_scholar_profile(html: str, name: str) -> dict:
    import re
    """解析 Google Scholar 搜索结果"""
    soup = BeautifulSoup(html, 'lxml')

    result = {
        "name": name,
        "status": "success",
        "scholar_profile_url": "",
        "scholar_id": "",
        "affiliation": "",
        "citations_all_time": 0,
        "citations_since_2019": 0,
        "h_index_all_time": 0,
        "h_index_since_2019": 0,
        "i10_index_all_time": 0,
        "i10_index_since_2019": 0,
        "recent_papers": [],
        "fields": [],
        "note": "Google Scholar 数据，需人工核实"
    }

    # 尝试找到用户个人主页链接
    profile_link = soup.find('a', href=re.compile(r'/citations\?user='))
    if profile_link:
        result['scholar_profile_url'] = profile_link.get('href', '')
        # 提取 scholar_id
        import re
        match = re.search(r'user=([^&]+)', result['scholar_profile_url'])
        if match:
            result['scholar_id'] = match.group(1)

    # 如果没有找到个人主页，尝试从搜索结果提取论文信息
    papers = []
    for item in soup.select('.gs_ri')[:5]:
        title_elem = item.select_one('.gs_rt a')
        if title_elem:
            papers.append({
                'title': title_elem.get_text(strip=True),
                'link': title_elem.get('href', ''),
            })
    result['recent_papers'] = papers

    return result


def search_cnki(name: str) -> dict:
    """
    查询知网CNKI导师信息

    注意: 知网需要登录或机构访问，此函数仅返回搜索链接。
    建议用户通过学校图书馆VPN访问后手动补充数据。
    """
    return {
        "name": name,
        "status": "manual_required",
        "cnki_search_url": f"https://kns.cnki.net/kns8/defaultresult/index?crossids=YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A&kw={quote(name)}&korder=SU",
        "note": "知网需通过学校VPN访问，请手动搜索后补充数据"
    }


def generate_profile_report(name: str, school: str, scholar_data: dict, cnki_data: dict) -> str:
    """生成导师学术画像报告"""
    lines = [
        f"# {name} — 学术画像",
        "",
        f"**所属学校**: {school}",
        f"**查询时间**: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Google Scholar",
        "",
    ]

    if scholar_data.get('status') == 'success':
        lines.extend([
            f"- **总引用数**: {scholar_data.get('citations_all_time', 'N/A')}",
            f"- **h-index**: {scholar_data.get('h_index_all_time', 'N/A')}",
            f"- **i10-index**: {scholar_data.get('i10_index_all_time', 'N/A')}",
            f"- **个人主页**: {scholar_data.get('scholar_profile_url', 'N/A')}",
            "",
            "### 近期论文",
            "",
        ])
        for paper in scholar_data.get('recent_papers', [])[:5]:
            lines.append(f"- {paper.get('title', 'N/A')}")
    else:
        lines.append(f"⚠️ 查询失败: {scholar_data.get('reason', '未知错误')}")
        lines.append("")
        lines.append("**建议**: 尝试通过以下方式手动查询:")
        lines.append(f"- Google Scholar: https://scholar.google.com/scholar?q={quote(name)}")

    lines.extend([
        "",
        "## 知网CNKI",
        "",
        f"- **搜索链接**: {cnki_data.get('cnki_search_url', 'N/A')}",
        f"- **说明**: {cnki_data.get('note', '')}",
        "",
        "## 综合评估",
        "",
        "| 维度 | 评分 | 说明 |",
        "|------|------|------|",
        "| 学术产出 | ⭐⭐⭐ | 待补充 |",
        "| 学术影响力 | ⭐⭐⭐ | 待补充 |",
        "| 近期活跃度 | ⭐⭐⭐ | 待补充 |",
        "",
        "## 数据来源",
        "",
        "- Google Scholar（需翻墙或镜像）",
        "- 知网CNKI（需学校VPN）",
        "- 学校官网（需手动补充）",
        "",
        "---",
        "",
        "> ⚠️ **注意**: 本报告为自动化生成，数据可能不完整。建议通过学校官网、知网、导师个人主页等渠道交叉验证。",
    ])

    return '\n'.join(lines)


def run_single(name: str, school: str = None, output_path: str = None):
    print(f"\n{'='*60}")
    print(f"导师学术信息查询: {name}")
    print(f"{'='*60}")

    print("\n[1] 查询 Google Scholar...")
    scholar_data = search_google_scholar(name, school)
    if scholar_data.get('status') == 'success':
        print(f"  ✓ 找到 {len(scholar_data.get('recent_papers', []))} 篇论文")
    else:
        print(f"  ✗ {scholar_data.get('reason', '查询失败')}")

    print("\n[2] 查询 知网CNKI...")
    cnki_data = search_cnki(name)
    print(f"  ℹ️  {cnki_data['note']}")

    report = generate_profile_report(name, school or "未知", scholar_data, cnki_data)

    final_output = output_path or os.path.join(DATA_DIR, f"{name}_profile.md")
    os.makedirs(os.path.dirname(final_output), exist_ok=True)
    with open(final_output, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n[保存] 报告 -> {final_output}")


def main():
    parser = argparse.ArgumentParser(description='导师学术信息查询')
    parser.add_argument('--name', help='导师姓名')
    parser.add_argument('--school', help='所属学校')
    parser.add_argument('--search-all', action='store_true', help='查询所有可用渠道')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--batch', action='store_true', help='批量模式（从文件读取）')
    parser.add_argument('--file', help='批量模式输入文件（JSON格式）')

    args = parser.parse_args()

    if args.batch:
        if not args.file:
            parser.error('--batch 模式必须提供 --file')
        with open(args.file, 'r', encoding='utf-8') as f:
            items = json.load(f)
        if not isinstance(items, list):
            parser.error('--file 必须是导师列表 JSON')

        for item in items:
            name = item.get('name')
            school = args.school or item.get('school') or item.get('college')
            if not name:
                continue
            run_single(name, school)
        print(f"\n{'='*60}")
        print("批量查询完成！")
        print(f"{'='*60}")
        return

    if not args.name:
        parser.error('非批量模式必须提供 --name')

    run_single(args.name, args.school, args.output)
    print(f"\n{'='*60}")
    print("查询完成！")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
