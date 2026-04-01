import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

URLS = {
    "top": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "eco": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "it": "https://news.yahoo.co.jp/rss/topics/it.xml",
    "int": "https://news.yahoo.co.jp/rss/topics/world.xml",
    "tgt": "https://togetter.com/rss/hot"
}

def fetch_rss_metadata(url, cat):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as res:
            xml_data = res.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
            desc = item.find('description').text if item.find('description') is not None else ''
            dt = None
            if pub_date_str:
                try:
                    dt = parsedate_to_datetime(pub_date_str)
                except Exception:
                    pass
            site = "togetter" if cat == "tgt" else "yahoo"
            items.append({"t": title, "l": link, "d": pub_date_str, "dt": dt, "cat": cat, "desc": desc, "site": site})
        return items
    except Exception as e:
        print(f"Error fetching {cat}: {e}")
        return []

def scrape_full_text(link, cat, desc):
    if cat == 'tgt':
        # Togetter requests generally block simple scraping or take too long.
        # So we use the robust description from RSS.
        content_text = desc if desc else "詳細なまとめはリンク先でご覧ください。"
        return content_text

    content_text = ""
    try:
        art_url = link
        if 'news.yahoo.co.jp/pickup/' in link:
            pickup_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(pickup_req, timeout=5) as p_res:
                p_soup = BeautifulSoup(p_res.read(), 'html.parser')
                next_a = p_soup.find('a', href=lambda h: h and 'news.yahoo.co.jp/articles/' in h)
                if next_a:
                    art_url = next_a['href']
                    
        art_req = urllib.request.Request(art_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(art_req, timeout=5) as art_res:
            html = art_res.read()
            soup = BeautifulSoup(html, 'html.parser')
            paragraphs = soup.select('div.article_body p.highLightSearchTarget, div.article_body p, .article_body p, p.highLightSearchTarget')
            if paragraphs:
                content_text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
            else:
                content_text = "本文の取得に失敗しました。元のリンクからお読みください。"
    except Exception as e:
        content_text = f"情報の取得に失敗しました。{e}"
    
    if len(content_text) > 2000:
        content_text = content_text[:2000] + "...\n(文字数制限により省略)"
    return content_text

def main():
    all_items = []
    for key, url in URLS.items():
        items = fetch_rss_metadata(url, key)
        valid_cat_items = [i for i in items if i['dt'] is not None]
        valid_cat_items.sort(key=lambda x: x['dt'], reverse=True)
        all_items.extend(valid_cat_items[:10])
    
    # Sort overall by datetime (newest first)
    all_items.sort(key=lambda x: x['dt'], reverse=True)
    
    # Scrape body for the selected items
    final_data = []
    for item in all_items:
        print(f"Scraping: {item['t']}")
        content = scrape_full_text(item['l'], item['cat'], item.get('desc', ''))
        final_data.append({
            "t": item["t"],
            "l": item["l"],
            "d": item["d"],
            "cat": item["cat"],
            "site": item.get("site", "yahoo"),
            "c": content
        })
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()

