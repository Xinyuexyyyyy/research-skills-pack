#!/usr/bin/env python3
"""
Supervisor Scout — 通用爬虫引擎（配置驱动）
=============================================
支持任意高校研招网的静态网站爬取，通过JSON配置适配不同网站结构。

用法:
    python3 crawler.py --config configs/bjut.json --mode list
    python3 crawler.py --config configs/bjut.json --mode full --max-pages 2
    python3 crawler.py --config configs/bjut.json --mode incremental
    python3 crawler.py --config configs/bjut.json --mode monitor --keywords 复试 调剂
    python3 crawler.py --config configs/bjut.json --mode list --channel master_notice
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# 添加项目根目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)


def load_config(config_path: str) -> Dict:
    """加载学校配置文件"""
    full_path = os.path.join(SKILL_DIR, config_path) if not os.path.isabs(config_path) else config_path
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class ConfigurableCrawler:
    """配置驱动的通用爬虫引擎"""

    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config['base_url'].rstrip('/')
        self.school_code = config['code']
        self.school_name = config['school']
        self.req_config = config.get('request', {})

        # HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.base_url + '/',
        })

        # 数据目录
        self.data_dir = os.path.join(SKILL_DIR, 'data', 'crawled', self.school_code)
        os.makedirs(self.data_dir, exist_ok=True)

    def _fetch(self, url: str, retries: int = None) -> Optional[str]:
        """获取网页内容"""
        retries = retries or self.req_config.get('retries', 3)
        timeout = self.req_config.get('timeout', 15)
        full_url = urljoin(self.base_url + '/', url)

        for attempt in range(retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(
                        self.req_config.get('min_delay', 1.0),
                        self.req_config.get('max_delay', 3.0)
                    ))

                response = self.session.get(full_url, timeout=timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return response.text

            except requests.RequestException as e:
                print(f"  [错误] 请求失败 ({attempt + 1}/{retries}): {full_url}")
                if attempt == retries - 1:
                    return None
                time.sleep(2 ** attempt)

        return None

    def _polite_delay(self):
        """礼貌延迟"""
        time.sleep(random.uniform(
            self.req_config.get('min_delay', 1.0),
            self.req_config.get('max_delay', 3.0)
        ))

    def _extract_article_id(self, href: str) -> str:
        """从URL提取文章ID"""
        match = re.search(r'/([^/]+)\.htm(?:\?.*)?$', href)
        return match.group(1) if match else ""

    def _resolve_url(self, href: str, base_url: str = None) -> str:
        """解析相对URL为绝对URL"""
        if href.startswith('http'):
            return href
        base = base_url or self.base_url + '/'
        # 去除相对路径前缀
        href = href.lstrip('./')
        return urljoin(base, href)

    def parse_list_page(self, html: str, channel_config: Dict) -> List[Dict]:
        """解析列表页"""
        soup = BeautifulSoup(html, 'lxml')
        selectors = channel_config['selectors']
        articles = []
        seen_urls = set()

        list_items = soup.select(selectors.get('list_container', 'div.text-list ul li'))

        for item in list_items:
            try:
                a_tag = item.find('a')
                if not a_tag:
                    continue

                href = a_tag.get('href', '')
                href = self._resolve_url(href)
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # 提取日期（支持多种格式）
                date_standard = ""
                date_dm_sel = selectors.get('date_day_month')
                date_y_sel = selectors.get('date_year')
                date_sel = selectors.get('date')

                if date_dm_sel and date_y_sel:
                    # 格式1: 北工大风格 <div class="date"><p>日-月</p><span>年</span></div>
                    dm_elem = item.select_one(date_dm_sel)
                    y_elem = item.select_one(date_y_sel)
                    if dm_elem and y_elem:
                        date_str = f"{y_elem.get_text(strip=True)}-{dm_elem.get_text(strip=True)}"
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                            date_standard = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            date_standard = date_str
                elif date_sel:
                    # 格式2: 北航风格 <span>YYYY-MM-DD</span>
                    date_elem = item.select_one(date_sel)
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        # 尝试匹配 YYYY-MM-DD
                        match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                        if match:
                            date_standard = match.group(1)
                        else:
                            date_standard = date_text

                # 提取标题
                title = ""
                title_sel = selectors.get('title', 'div.text-h3')
                title_elem = item.select_one(title_sel)
                if title_elem:
                    title = title_elem.get_text(strip=True)

                articles.append({
                    'article_id': self._extract_article_id(href),
                    'title': title,
                    'date': date_standard,
                    'url': href,
                    'channel': channel_config['name'],
                    'crawled_at': datetime.now().isoformat(),
                })

            except Exception as e:
                print(f"  [警告] 解析单项失败: {e}")
                continue

        return articles

    def parse_detail_page(self, html: str, article_id: str, selectors: Dict) -> Dict:
        """解析详情页"""
        soup = BeautifulSoup(html, 'lxml')
        result = {
            'article_id': article_id,
            'title': '',
            'publish_date': '',
            'content_text': '',
            'content_html': '',
        }

        try:
            # 标题
            title_sel = selectors.get('detail_title', 'div.art-tit h3')
            title_elem = soup.select_one(title_sel)
            if title_elem:
                result['title'] = title_elem.get_text(strip=True)

            # 发布日期
            date_sel = selectors.get('detail_date', 'div.art-tit span')
            date_elem = soup.select_one(date_sel)
            if date_elem:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_elem.get_text())
                if date_match:
                    result['publish_date'] = date_match.group(1)

            # 正文
            content_sel = selectors.get('detail_content', 'div#vsb_content')
            content_elem = soup.select_one(content_sel)
            if content_elem:
                result['content_text'] = content_elem.get_text(separator='\n', strip=True)
                result['content_html'] = str(content_elem)

        except Exception as e:
            print(f"  [警告] 解析详情页失败: {e}")

        return result

    def get_pagination_urls(self, html: str, channel_config: Dict) -> List[str]:
        """获取分页URL列表"""
        pagination = channel_config.get('pagination', {})
        pagination_type = pagination.get('type')
        if pagination_type == 'none':
            return []

        soup = BeautifulSoup(html, 'lxml')
        urls = []

        if pagination_type == 'reverse_numbered':
            # 北工大风格：倒序分页
            pag_div = soup.find('div', class_='pagination')
            if pag_div:
                page_links = pag_div.find_all('a', href=re.compile(r'/\d+\.htm'))
                page_numbers = []
                for link in page_links:
                    match = re.search(r'/(\d+)\.htm', link.get('href', ''))
                    if match:
                        page_numbers.append(int(match.group(1)))

                if page_numbers:
                    max_num = max(page_numbers)
                    list_url = channel_config['list_url']
                    base_path = list_url.replace('.htm', '')

                    # 第1页
                    urls.append(list_url)
                    # 后续页
                    for i in range(max_num, 0, -1):
                        urls.append(f"{base_path}/{i}.htm")

        elif pagination_type == 'numbered_zero_based':
            first_page = pagination.get('first_page', channel_config['list_url'])
            pattern = pagination.get('pattern')
            page_num_offset = pagination.get('page_num_offset', 0)
            hrefs = [a.get('href', '') for a in soup.find_all('a', href=True)]
            page_numbers = []

            for href in hrefs:
                match = re.search(r'index(\d+)\.htm', href)
                if match:
                    page_numbers.append(int(match.group(1)))

            if page_numbers and pattern:
                urls.append(first_page)
                max_num = max(page_numbers)
                for page_num in range(page_num_offset + 2, max_num + 1):
                    urls.append(pattern.format(page_num=page_num))

        return urls

    def crawl_channel(self, channel_key: str, max_pages: int = 0) -> List[Dict]:
        """爬取单个栏目"""
        channel = self.config['channels'][channel_key]
        print(f"\n{'='*60}")
        print(f"[{self.school_name}] {channel['name']}")
        print(f"{'='*60}")

        all_articles = []

        # 获取第1页
        list_url = channel['list_url']
        print(f"\n[1] 获取: {list_url}")
        html = self._fetch(list_url)
        if not html:
            print("  [错误] 第1页获取失败")
            return all_articles

        articles = self.parse_list_page(html, channel)
        all_articles.extend(articles)
        print(f"  提取 {len(articles)} 条")

        # 分页
        page_urls = self.get_pagination_urls(html, channel)
        if len(page_urls) > 1:
            print(f"  检测到分页，总页数: {len(page_urls)}")

            pages_to_crawl = page_urls[1:]  # 去掉第1页
            if max_pages > 0:
                pages_to_crawl = pages_to_crawl[:max_pages - 1]

            for i, page_url in enumerate(pages_to_crawl, start=2):
                print(f"\n[{i}] 获取: {page_url}")
                self._polite_delay()

                html = self._fetch(page_url)
                if not html:
                    print("  [错误] 获取失败，跳过")
                    continue

                articles = self.parse_list_page(html, channel)
                all_articles.extend(articles)
                print(f"  提取 {len(articles)} 条")

        print(f"\n[完成] 共 {len(all_articles)} 条")
        return all_articles

    def crawl_all_channels(self, max_pages: int = 0) -> Dict[str, List[Dict]]:
        """爬取所有栏目"""
        results = {}
        for channel_key in self.config['channels']:
            results[channel_key] = self.crawl_channel(channel_key, max_pages)
        return results

    def crawl_details(self, articles: List[Dict], channel_key: str) -> List[Dict]:
        """爬取详情页"""
        channel = self.config['channels'][channel_key]
        selectors = channel['selectors']

        print(f"\n{'='*60}")
        print(f"开始爬取详情页: {len(articles)} 条")
        print(f"{'='*60}")

        results = []
        for i, article in enumerate(articles, 1):
            print(f"\n[{i}/{len(articles)}] {article['title'][:40]}...")
            self._polite_delay()

            # 详情页URL需要去掉域名前缀，转为相对路径
            detail_url = article['url']
            if detail_url.startswith(self.base_url):
                detail_url = detail_url[len(self.base_url):].lstrip('/')

            html = self._fetch(detail_url)
            if not html:
                print("  [错误] 详情页获取失败")
                continue

            detail = self.parse_detail_page(html, article['article_id'], selectors)
            merged = {**article, **detail}
            results.append(merged)
            print(f"  内容: {len(detail['content_text'])} 字符")

        print(f"\n[完成] 共 {len(results)} 条详情")
        return results

    def incremental_update(self, channel_key: str = 'latest_notice') -> List[Dict]:
        """增量更新"""
        print(f"\n{'='*60}")
        print(f"增量更新: [{self.school_name}] {self.config['channels'][channel_key]['name']}")
        print(f"{'='*60}")

        # 读取已有状态
        state_file = os.path.join(self.data_dir, 'state.json')
        existing_ids = set()
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                existing_ids = set(state.get('article_ids', []))
            print(f"已有 {len(existing_ids)} 条记录")

        # 爬取列表
        channel = self.config['channels'][channel_key]
        html = self._fetch(channel['list_url'])
        if not html:
            print("[错误] 列表页获取失败")
            return []

        articles = self.parse_list_page(html, channel)
        new_articles = []

        for article in articles:
            if article['article_id'] in existing_ids:
                print(f"  [跳过] 已存在: {article['title'][:30]}...")
                break
            new_articles.append(article)
            print(f"  [新] {article['title'][:40]}...")

        if new_articles:
            # 更新状态
            all_ids = existing_ids | {a['article_id'] for a in new_articles}
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'article_ids': list(all_ids),
                    'last_update': datetime.now().isoformat(),
                    'channel': channel_key,
                    'school': self.school_code,
                }, f, ensure_ascii=False, indent=2)

            # 保存新增数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_json(new_articles, f"{channel_key}_new_{timestamp}.json", subdir=channel_key)

            print(f"\n[增量更新完成] 新增 {len(new_articles)} 条")

            # 检查关键词匹配
            keywords = self.config.get('monitor_keywords', [])
            matched = self._keyword_match(new_articles, keywords)
            if matched:
                self._print_alert(matched)
                self.save_json(matched, f"{channel_key}_alerts_{timestamp}.json", subdir=channel_key)
        else:
            print("\n[增量更新完成] 无新数据")

        return new_articles

    def keyword_monitor(self, keywords: List[str], channel_key: str = 'latest_notice', max_pages: int = 2) -> List[Dict]:
        """关键词监控"""
        print(f"\n{'='*60}")
        print(f"关键词监控: {', '.join(keywords)}")
        print(f"栏目: {self.config['channels'][channel_key]['name']}")
        print(f"{'='*60}")

        articles = self.crawl_channel(channel_key, max_pages)
        matched = self._keyword_match(articles, keywords)

        if matched:
            self._print_alert(matched)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_json(matched, f"{channel_key}_monitor_{timestamp}.json", subdir=channel_key)
        else:
            print("\n未匹配到任何结果")

        return matched

    def _keyword_match(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """关键词匹配"""
        matched = []
        for article in articles:
            text = f"{article['title']} {article.get('channel', '')}"
            for keyword in keywords:
                if keyword in text:
                    matched.append({**article, 'matched_keyword': keyword})
                    break
        return matched

    def _print_alert(self, matched: List[Dict]):
        """打印提醒"""
        print(f"\n{'='*60}")
        print(f"⚠️  监控提醒: 匹配 {len(matched)} 条")
        print(f"{'='*60}")
        for item in matched:
            print(f"\n📌 [{item['matched_keyword']}] {item['title']}")
            print(f"   📅 {item['date']}")
            print(f"   🔗 {item['url']}")

    def save_json(self, data: List[Dict], filename: str, subdir: str = ''):
        """保存JSON"""
        dir_path = os.path.join(self.data_dir, subdir) if subdir else self.data_dir
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[保存] JSON -> {filepath} ({len(data)} 条)")

    def save_csv(self, data: List[Dict], filename: str, subdir: str = ''):
        """保存CSV"""
        if not data:
            return
        dir_path = os.path.join(self.data_dir, subdir) if subdir else self.data_dir
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)

        list_fields = ['article_id', 'title', 'date', 'url', 'channel', 'crawled_at']
        if 'content_text' in data[0]:
            list_fields.append('content_text')

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list_fields)
            writer.writeheader()
            for item in data:
                row = {k: item.get(k, '') for k in list_fields}
                if 'content_text' in row and len(str(row['content_text'])) > 5000:
                    row['content_text'] = str(row['content_text'])[:5000] + '...'
                writer.writerow(row)

        print(f"[保存] CSV -> {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Supervisor Scout — 通用爬虫引擎')
    parser.add_argument('--config', required=True, help='配置文件路径 (如 configs/bjut.json)')
    parser.add_argument('--mode', choices=['list', 'full', 'incremental', 'monitor', 'all'],
                        default='list', help='爬取模式')
    parser.add_argument('--channel', default='latest_notice',
                        help='栏目key (默认latest_notice，all模式爬全部)')
    parser.add_argument('--max-pages', type=int, default=0, help='最大页数 (0=全部)')
    parser.add_argument('--keywords', nargs='+', help='监控关键词')
    parser.add_argument('--output-dir', help='输出目录覆盖')

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    print(f"\n🏫 目标学校: {config['school']} ({config['code']})")
    print(f"🔗 研招网: {config['base_url']}")

    # 初始化爬虫
    crawler = ConfigurableCrawler(config)
    if args.output_dir:
        crawler.data_dir = args.output_dir

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.mode == 'list':
        # 只爬列表
        articles = crawler.crawl_channel(args.channel, args.max_pages)
        if articles:
            crawler.save_json(articles, f"{args.channel}_list_{timestamp}.json", args.channel)
            crawler.save_csv(articles, f"{args.channel}_list_{timestamp}.csv", args.channel)

    elif args.mode == 'full':
        # 爬列表+详情
        articles = crawler.crawl_channel(args.channel, args.max_pages)
        if articles:
            full_data = crawler.crawl_details(articles, args.channel)
            crawler.save_json(full_data, f"{args.channel}_full_{timestamp}.json", args.channel)
            crawler.save_csv(full_data, f"{args.channel}_full_{timestamp}.csv", args.channel)

    elif args.mode == 'incremental':
        # 增量更新
        crawler.incremental_update(args.channel)

    elif args.mode == 'monitor':
        # 关键词监控
        keywords = args.keywords or config.get('monitor_keywords', [])
        if not keywords:
            print("[错误] 未指定关键词，且配置中无默认关键词")
            return
        crawler.keyword_monitor(keywords, args.channel, args.max_pages)

    elif args.mode == 'all':
        # 爬取所有栏目
        results = crawler.crawl_all_channels(args.max_pages)
        for ch_key, articles in results.items():
            if articles:
                crawler.save_json(articles, f"{ch_key}_list_{timestamp}.json", ch_key)

    print(f"\n{'='*60}")
    print("爬取完成！")
    print(f"数据目录: {os.path.abspath(crawler.data_dir)}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
