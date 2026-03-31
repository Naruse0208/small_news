import urllib.request
import xml.etree.ElementTree as ET
import json
import os

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
    # 帯域節約のため主要な記事10件程度に絞るか、またはそのまま返す。まずは全て返す
    count = 0
    for item in root.findall('./channel/item'):
        if count >= 15: # 15件制限でさらなる軽量化
            break
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else ''
        # Yahoo RSSの日付フォーマット "Mon, 31 Mar 2026 10:00:00 GMT"等。長いので削るなどの処理も可能だがまずはそのままか少し削る
        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
        
        # 不要なパラメータを削る軽量化: t=title, l=link, d=date
        items.append({"t": title, "l": link, "d": pub_date})
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
        # separators=(',', ':')を指定してスペースを完全に排除
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
