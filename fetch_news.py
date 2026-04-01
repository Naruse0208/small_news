import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

URLS = {
    "top": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "dom": "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "eco": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "ent": "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
    "spo": "https://news.yahoo.co.jp/rss/topics/sports.xml",
    "it": "https://news.yahoo.co.jp/rss/topics/it.xml",
    "sci": "https://news.yahoo.co.jp/rss/topics/science.xml",
    "loc": "https://news.yahoo.co.jp/rss/topics/local.xml",
    "int": "https://news.yahoo.co.jp/rss/topics/world.xml",
    "tgt_hot": "https://togetter.com/rss/hot",
    "tgt_rec": "https://togetter.com/rss/recent",
    "tgt_idx": "https://togetter.com/rss/index",
    # TogetterはRSSだけだと数件しかとれないため、複数から引っ張る
}

# 少ない通信量にするための文字数制限
MAX_TEXT_LEN = 250

def fetch_rss_metadata(url, cat):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
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
            site = "togetter" if cat.startswith("tgt") else "yahoo"
            # 表示上わかりやすいようにtgt_* は 'tgt' にまとめる
            disp_cat = "tgt" if cat.startswith("tgt") else cat
            items.append({"t": title, "l": link, "d": pub_date_str, "dt": dt, "cat": disp_cat, "desc": desc, "site": site})
        return items
    except Exception as e:
        print(f"Error fetching {cat}: {e}")
        return []

def scrape_full_text(link, site, desc):
    content_text = ""
    try:
        if site == 'togetter':
            # Togetterのスクレイピング (本文からテキストを抽出)
            tgt_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(tgt_req, timeout=5) as tgt_res:
                soup = BeautifulSoup(tgt_res.read(), 'html.parser')
                # 記事本体っぽいいくつかの要素からテキストを抜き出す
                tweets = soup.select('.tweet_body, .list_tweet_box, .tweet_box, .comment_box')
                if tweets:
                    content_text = "\n\n".join(t.get_text(separator=' ', strip=True) for t in tweets[:5])
                else:
                    # うまく取れなければbodyから抽出（ヘッダなどを避けるため #__next や main 等）
                    main_box = soup.find(id='__next') or soup.find('body')
                    if main_box:
                        content_text = main_box.get_text(separator=' ', strip=True)
                        # 不要なナビゲーションテキストをスキップするため、最初の方を飛ばす工夫（簡易的）
                        content_text = content_text[content_text.find("まとめ"): ] if "まとめ" in content_text else content_text
                
                # パースできなかったり短すぎたらRSSのDescriptionも使う
                if len(content_text) < 20 and desc:
                    content_text = desc + "\n\n" + content_text
        else:
            # Yahooのスクレイピング
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
                soup = BeautifulSoup(art_res.read(), 'html.parser')
                paragraphs = soup.select('div.article_body p.highLightSearchTarget, div.article_body p, .article_body p, p.highLightSearchTarget')
                if paragraphs:
                    content_text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
                else:
                    content_text = desc if desc else "本文の取得に失敗しました。元のリンクからお読みください。"
                    
    except Exception as e:
        content_text = f"情報の取得に失敗しました。{e}"
    
    # 文字数制限（制限下での通信量節約）
    if len(content_text) > MAX_TEXT_LEN:
        content_text = content_text[:MAX_TEXT_LEN] + "...\n(省略: 詳細や続きはオリジナルサイトで)"
    return content_text

def main():
    yahoo_items = []
    togetter_items = []
    
    for key, url in URLS.items():
        items = fetch_rss_metadata(url, key)
        valid_items = [i for i in items if i['dt'] is not None]
        for item in valid_items:
            if item['site'] == 'yahoo':
                yahoo_items.append(item)
            else:
                togetter_items.append(item)
    
    # 重複排除とソート
    def filter_unique_and_sort(item_list, limit=100):
        unique_urls = set()
        unique_items = []
        for item in sorted(item_list, key=lambda x: x['dt'], reverse=True):
            if item['l'] not in unique_urls:
                unique_urls.add(item['l'])
                unique_items.append(item)
                if len(unique_items) >= limit:
                    break
        return unique_items

    # それぞれ100件まで取得
    yahoo_top_100 = filter_unique_and_sort(yahoo_items, 100)
    togetter_top_100 = filter_unique_and_sort(togetter_items, 100)
    
    all_selected = yahoo_top_100 + togetter_top_100
    all_selected.sort(key=lambda x: x['dt'], reverse=True)
    
    final_data = []
    # Scraping sequentially might take some time (200 requests = maybe 1-2 minutes)
    for i, item in enumerate(all_selected):
        print(f"[{i+1}/{len(all_selected)}] Scraping: {item['t']}")
        content = scrape_full_text(item['l'], item['site'], item.get('desc', ''))
        final_data.append({
            "t": item["t"],
            "l": item["l"],
            "d": item["d"],
            "cat": item["cat"],
            "site": item["site"],
            "c": content
        })
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
