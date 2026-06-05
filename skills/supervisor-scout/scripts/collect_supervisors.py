#!/usr/bin/env python3
"""
Supervisor Scout — 导师名单采集
================================
从各高校官网采集博硕导师名单。

用法:
    python3 collect_supervisors.py --school bjut --college jxny
    python3 collect_supervisors.py --school bit --college me_vehicle
    python3 collect_supervisors.py --school bit --college me_energy
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def fetch(url: str, timeout: int = 15, retries: int = 3) -> Optional[str]:
    """获取网页内容"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"  [错误] 请求失败: {url} - {e}")
                return None
            time.sleep(1)
    return None


def looks_like_person_name(name: str) -> bool:
    """粗略判断是否像导师姓名，兼容中文名和少量英文名"""
    if not name:
        return False

    text = re.sub(r"\s+", " ", name).strip()
    if len(text) < 2 or len(text) > 40:
        return False

    blocked_keywords = [
        '首页', '学院', '专业', '招生', '通知', '返回', '更多', '简介', '概况',
        '历史沿革', '领导团队', '治理机构', '下载中心', '学校主页', 'English',
        '车辆工程系', '能源与动力工程系', '智能制造系', '基础教学与实验创新中心',
    ]
    if any(keyword in text for keyword in blocked_keywords):
        return False

    if re.fullmatch(r'[\u4e00-\u9fff·]{2,8}', text):
        return True

    if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,39}", text):
        return True

    return False


# ==================== 北工大 ====================

BJUT_COLLEGES = {
    "jxny": {"name": "机械与能源工程学院", "url": "https://jxny.bjut.edu.cn/szdw/dsd/bssds.htm"},
    "clxy": {"name": "材料科学与工程学院", "url": "https://clxy.bjut.edu.cn/szdw/szgk.htm"},
    "sist": {"name": "信息科学技术学院", "url": "https://sist.bjut.edu.cn/szdw/dwgk.htm"},
    "cs": {"name": "计算机学院", "url": "https://cs.bjut.edu.cn/szdw/dsdw/bssds.htm"},
    "cace": {"name": "建筑工程学院", "url": "https://cace.bjut.edu.cn/szdw/jsjs.htm"},
    "caup": {"name": "建筑与城市规划学院", "url": "https://caup.bjut.edu.cn/yjsjy/dsjs1/xsxwsssds.htm"},
    "cmt": {"name": "城市交通学院", "url": "https://cmt.bjut.edu.cn/sddw/dsdw1/bssds.htm"},
    "cese": {"name": "环境科学与工程学院", "url": "https://cese.bjut.edu.cn/rcpy/yjspy/sssds.htm"},
    "hsxy": {"name": "化学与生命科学学院", "url": "https://hsxy.bjut.edu.cn/jyjx/yjsjy/xwdjs.htm"},
    "spoe": {"name": "物理与光电工程学院", "url": "https://spoe.bjut.edu.cn/szdw/dsdw/bssds.htm"},
    "msm": {"name": "数学统计学与力学学院", "url": "https://msm.bjut.edu.cn/szdw1/dsdw/bssds.htm"},
    "fhss": {"name": "社会学院", "url": "https://fhss.bjut.edu.cn/index.htm"},
    "cfl": {"name": "外国语学院", "url": "https://cfl.bjut.edu.cn/szdw/dsdw.htm"},
    "jjyglxy": {"name": "经济与管理学院", "url": "https://jjyglxy.bjut.edu.cn/szdw/dsdw1/xsxwbssds.htm"},
    "marx": {"name": "马克思主义学院", "url": "https://marx.bjut.edu.cn/yjspy/yjsds1/xsxwyjsds.htm"},
    "bjiad": {"name": "艺术设计学院", "url": "https://bjiad.bjut.edu.cn/szdw/jsdw.htm"},
}


def parse_bjut_me_supervisors(html: str, college_name: str) -> List[Dict]:
    """解析北工大机械学院博硕导师页面"""
    soup = BeautifulSoup(html, 'lxml')
    supervisors = []

    for h2 in soup.find_all('h2'):
        category = h2.get_text(strip=True)
        ul = h2.find_next_sibling()
        if not ul or ul.name != 'ul':
            ul = h2.find_parent().find_next_sibling()
        if not ul or ul.name != 'ul':
            continue

        for li in ul.find_all('li'):
            a_tag = li.find('a')
            if not a_tag:
                continue
            name = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            if not name or name == '#' or len(name) < 2:
                continue

            if href.startswith('http'):
                profile_url = href
            elif href.startswith('../../'):
                profile_url = urljoin("https://jxny.bjut.edu.cn/szdw/dsd/", href)
            elif href.startswith('/'):
                profile_url = "https://jxny.bjut.edu.cn" + href
            else:
                profile_url = urljoin("https://jxny.bjut.edu.cn/szdw/dsd/", href)

            supervisors.append({
                'name': name,
                'college': college_name,
                'category': category,
                'profile_url': profile_url,
                'source': 'jxny.bjut.edu.cn',
                'collected_at': datetime.now().isoformat(),
            })

    return supervisors


def parse_generic_supervisors(html: str, college_name: str, base_url: str) -> List[Dict]:
    """通用导师页面解析"""
    soup = BeautifulSoup(html, 'lxml')
    supervisors = []

    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            a_tag = li.find('a')
            if not a_tag:
                continue
            name = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            if not name or len(name) < 2 or len(name) > 10:
                continue
            if any(kw in name for kw in ['首页', '学院', '专业', '招生', '通知', '返回']):
                continue

            if href.startswith('http'):
                profile_url = href
            else:
                profile_url = urljoin(base_url, href)

            supervisors.append({
                'name': name,
                'college': college_name,
                'category': '未知',
                'profile_url': profile_url,
                'source': base_url,
                'collected_at': datetime.now().isoformat(),
            })

    seen = set()
    unique = []
    for s in supervisors:
        key = (s['name'], s['college'])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def collect_bjut_supervisors(target_college: str = None) -> Dict[str, List[Dict]]:
    """采集北工大导师名单"""
    print(f"\n{'='*60}")
    print("北工大导师名单采集")
    print(f"{'='*60}")

    results = {}
    colleges_to_process = {target_college: BJUT_COLLEGES[target_college]} if target_college else BJUT_COLLEGES

    for code, info in colleges_to_process.items():
        college_name = info['name']
        url = info['url']

        print(f"\n[{code}] {college_name}")
        print(f"  URL: {url}")

        html = fetch(url)
        if not html:
            print(f"  [跳过] 页面获取失败")
            continue

        if code == 'jxny':
            supervisors = parse_bjut_me_supervisors(html, college_name)
        else:
            supervisors = parse_generic_supervisors(html, college_name, url)

        results[code] = supervisors
        print(f"  采集 {len(supervisors)} 位导师")
        time.sleep(1)

    return results


# ==================== 北理工 ====================

def parse_bit_me_supervisors(html: str, college_name: str, base_url: str) -> List[Dict]:
    """
    解析北理工机械与车辆学院教师页面。

    仅在导师列表容器 `div.stuCol` 内抓取，避免将整页导航误识别为导师。
    典型结构:

    <div class="stuCol">
      <h3>研究所名称</h3>
      <div class="stuCol_con">
        <div class="stu_left"><h3>正高级职称</h3></div>
        <div class="stu_right"><dl><dd><a href="...">姓名</a></dd>...</dl></div>
      </div>
    </div>
    """
    soup = BeautifulSoup(html, 'lxml')
    supervisors = []

    for block in soup.select('div.stuCol'):
        institute_h3 = block.find('h3', recursive=False)
        if not institute_h3:
            continue

        institute = institute_h3.get_text(strip=True)
        if not institute:
            continue

        for group in block.select('div.stuCol_con'):
            title_h3 = group.select_one('div.stu_left h3')
            title_rank = title_h3.get_text(strip=True) if title_h3 else ''
            category = institute if not title_rank else f"{institute} | {title_rank}"

            for a_tag in group.select('div.stu_right a[href]'):
                name = a_tag.get_text(strip=True)
                if not looks_like_person_name(name):
                    continue

                href = a_tag.get('href', '').strip()
                if not href:
                    continue

                profile_url = href if href.startswith('http') else urljoin(base_url, href)
                supervisors.append({
                    'name': name,
                    'college': college_name,
                    'category': category,
                    'profile_url': profile_url,
                    'source': base_url,
                    'collected_at': datetime.now().isoformat(),
                })

    seen = set()
    unique = []
    for s in supervisors:
        key = (s['name'], s['college'], s['category'])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def collect_bit_supervisors(target_college: str = None) -> Dict[str, List[Dict]]:
    """采集北理工导师名单"""
    print(f"\n{'='*60}")
    print("北理工导师名单采集")
    print(f"{'='*60}")

    # 加载配置
    config_path = os.path.join(SKILL_DIR, 'configs', 'bit.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    colleges = config.get('colleges', {})
    results = {}

    colleges_to_process = {target_college: colleges[target_college]} if target_college else colleges

    for code, info in colleges_to_process.items():
        college_name = info['name']
        url = info['url']

        print(f"\n[{code}] {college_name}")
        print(f"  URL: {url}")

        html = fetch(url)
        if not html:
            print(f"  [跳过] 页面获取失败")
            continue

        supervisors = parse_bit_me_supervisors(html, college_name, url)
        results[code] = supervisors
        print(f"  采集 {len(supervisors)} 位导师")

        # 统计各研究所/职称分布
        institutes = {}
        for s in supervisors:
            inst = s['category'].split(' | ')[0] if ' | ' in s['category'] else s['category']
            institutes[inst] = institutes.get(inst, 0) + 1
        for inst, count in institutes.items():
            if inst:
                print(f"    - {inst}: {count}人")

        time.sleep(1)

    return results


# ==================== 保存结果 ====================

def save_results(results: Dict[str, List[Dict]], school_code: str):
    """保存采集结果"""
    output_dir = os.path.join(SKILL_DIR, 'data', 'processed', school_code)
    os.makedirs(output_dir, exist_ok=True)

    # 保存分学院文件
    for college_code, supervisors in results.items():
        filepath = os.path.join(output_dir, f"{college_code}_supervisors.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(supervisors, f, ensure_ascii=False, indent=2)

    # 汇总当前目录下所有 *_supervisors.json，避免单学院执行时覆盖其他学院数据
    all_supervisors = []
    college_stats = []
    for filename in sorted(os.listdir(output_dir)):
        if not filename.endswith('_supervisors.json'):
            continue
        if filename == 'all_supervisors.json':
            continue
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            supervisors = json.load(f)
        if not isinstance(supervisors, list):
            continue
        all_supervisors.extend(supervisors)
        college_name = supervisors[0]['college'] if supervisors else filename.replace('_supervisors.json', '')
        college_stats.append((college_name, len(supervisors)))

    summary_path = os.path.join(output_dir, "all_supervisors.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_supervisors, f, ensure_ascii=False, indent=2)

    # 生成统计报告
    report_lines = [
        f"# {school_code.upper()} 导师采集报告",
        "",
        f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**导师总数**: {len(all_supervisors)}",
        "",
        "## 各学院统计",
        "",
        "| 学院 | 导师人数 |",
        "|------|----------|",
    ]
    for college_name, count in college_stats:
        report_lines.append(f"| {college_name} | {count} |")

    report_lines.extend([
        "",
        "## 数据文件",
        "",
        f"- 汇总数据: `{summary_path}`",
        f"- 分学院数据: `{output_dir}/*_supervisors.json`",
    ])

    report_path = os.path.join(output_dir, "collection_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n{'='*60}")
    print(f"[保存] 汇总: {summary_path} ({len(all_supervisors)} 位导师)")
    print(f"[保存] 报告: {report_path}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='导师名单采集')
    parser.add_argument('--school', default='bjut', help='学校代码 (bjut/buaa/bit)')
    parser.add_argument('--college', help='指定学院代码')

    args = parser.parse_args()

    if args.school == 'bjut':
        results = collect_bjut_supervisors(args.college)
        save_results(results, args.school)
    elif args.school == 'bit':
        results = collect_bit_supervisors(args.college)
        save_results(results, args.school)
    else:
        print(f"[错误] 暂不支持学校: {args.school}")

    print("\n采集完成！")


if __name__ == '__main__':
    main()
