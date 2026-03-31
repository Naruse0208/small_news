import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import re
from bs4 import BeautifulSoup

URLS = {
    "top": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "eco": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "it": "https://news.yahoo.co.jp/rss/topics/it.xml",
    "int": "https://news.yahoo.co.jp/rss/topics/world.xml"
}

def fetch_rss(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as res:
        xml_data = res.read()
    root = ET.fromstring(xml_data)
    items = []
    count = 0
    for item in root.findall('./channel/item'):
        if count >= 10: # 軽量化と処理速度のため10件に制限
            break
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else ''
        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
        
        # ----- 全文スクレイピング -----
        content_text = ""
        try:
            art_url = link
            # YahooのRSSは /pickup/ のリンクを返すことが多いため、実際の記事URLを探す
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
                # Yahooニュースは通常、'.article_body' や 'p.highLightSearchTarget' などの中に段落本文がある
                paragraphs = soup.select('div.article_body p.highLightSearchTarget, div.article_body p, .article_body p, p.highLightSearchTarget')
                if paragraphs:
                    content_text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
                else:
                    content_text = "本文の取得に失敗しました。元のリンクからお読みください。"
        except Exception as e:
            content_text = f"情報の取得に失敗しました。{e}"
        
        # 文字数制限（2000文字程度を上限とする）
        if len(content_text) > 2000:
            content_text = content_text[:2000] + "...\n(文字数制限により省略)"

        items.append({"t": title, "l": link, "d": pub_date, "c": content_text})
        count += 1
        
    return items

def main():
    data = {}
    for key, url in URLS.items():
        try:
            data[key] = fetch_rss(url)
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            data[key] = []
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        # separatorsを指定し、改行等のエスケープ文字の容量も抑える
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()

