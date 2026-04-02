import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime, timezone
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
}

def fetch_yahoo_rss():
    items = []
    for cat, url in URLS.items():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                xml_data = res.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item'):
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
                desc = item.find('description').text if item.find('description') is not None else ''
                dt = None
                if pub_date_str:
                    try:
                        dt = parsedate_to_datetime(pub_date_str).astimezone(timezone.utc)
                    except Exception:
                        pass
                
                # Yahoo記事の場合はPV取得不可のため空文字列、時間はdtから相対時間をフロント側で作ってもらう等
                items.append({
                    "t": title, "l": link, 
                    "d": pub_date_str, "dt": dt, 
                    "cat": cat, "desc": desc, "site": "yahoo", 
                    "pv": "", "time": ""
                })
        except Exception as e:
            print(f"Error fetching {cat}: {e}")
    return items

def fetch_togetter_recent(limit=50):
    items = []
    seen = set()
    page = 1
    
    while len(items) < limit and page <= 3:
        req_url = f"https://togetter.com/recent?page={page}"
        req = urllib.request.Request(req_url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                soup = BeautifulSoup(res.read(), 'html.parser')
                links = soup.find_all('a', href=lambda x: x and '/li/' in x)
                
                for l in links:
                    href = l.get('href')
                    if not href.startswith('http'):
                        href = 'https://togetter.com' + href
                    if href in seen: continue
                    seen.add(href)
                    
                    title = l.get_text(strip=True)
                    if not title: continue
                    
                    # 親要素からメタデータを漁る
                    pv_text = ""
                    time_text = ""
                    if l.parent and l.parent.parent:
                        parent_text = l.parent.parent.get_text(" ", strip=True)
                        m_pv = re.search(r'(\d+)\s*pv', parent_text, re.IGNORECASE)
                        m_time = re.search(r'(\d+[分時間日前]+)', parent_text)
                        if m_pv: pv_text = m_pv.group(1)
                        if m_time: time_text = m_time.group(1)
                        
                    items.append({
                        "t": title, "l": href,
                        "d": "", "dt": None,  # Togetterは正確な日時オブジェクトなし
                        "cat": "tgt", "desc": "", "site": "togetter",
                        "pv": pv_text, "time": time_text
                    })
                    
                    if len(items) >= limit:
                        break
        except Exception as e:
            print(f"Error fetching togetter page {page}: {e}")
            break
        page += 1
    return items

def fetch_gigazine_rss(limit=50):
    items = []
    url = "https://gigazine.net/news/rss_2.0/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            xml_data = res.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
            desc = item.find('description').text if item.find('description') is not None else ''
            dt = None
            if pub_date_str:
                try:
                    dt = parsedate_to_datetime(pub_date_str).astimezone(timezone.utc)
                except Exception:
                    pass
            
            items.append({
                "t": title, "l": link, 
                "d": pub_date_str, "dt": dt, 
                "cat": "ggz", "desc": desc, "site": "gigazine", 
                "pv": "", "time": ""
            })
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"Error fetching GIGAZINE: {e}")
    return items

def scrape_full_text(link, site, desc):
    content_text = ""
    try:
        if site == 'togetter':
            tgt_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(tgt_req, timeout=5) as tgt_res:
                soup = BeautifulSoup(tgt_res.read(), 'html.parser')
                # 1ページ目のツイート群を取得
                tweets = soup.select('.type_tweet, .tweet_list .list_item, .tweet_box, div[data-tweet]')
                if tweets:
                    extracted = []
                    for t in tweets:
                        # 投稿者名、アイコン、リンクなどの不要情報を削除
                        # .tweet_footer に日付等が含まれることがあるのでそれも追加
                        for unwanted in t.select('.status_name, .user_link, .icon, .tw-user, a[href*="/user/"], .timestamp, .tweet_footer, .link_box'):
                            unwanted.decompose()
                        # テキストのみ取り出し
                        text = t.get_text('\n', strip=True)
                        # 不要なx.comリンクや日時テキストへのfallback (正規表現による掃除)
                        text = re.sub(r'x\.com/[^\s]+', '', text)
                        text = re.sub(r'twitter\.com/[^\s]+', '', text)
                        text = re.sub(r'pic\.x\.com/[^\s]+', '', text)
                        text = re.sub(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', '', text)
                        text = re.sub(r'[@＠][a-zA-Z0-9_]+', '', text)
                        
                        # 余分な改行を整理
                        text = '\n'.join([line for line in text.split('\n') if line.strip()])
                        if text:
                            extracted.append(text)
                    # ポスト間に十分な改行を入れて見やすくする
                    content_text = "\n\n\n".join(extracted)
                
                if not content_text:
                    # うまく取れなければフォールバック
                    main_box = soup.find(id='__next') or soup.find('body')
                    if main_box:
                        raw_text = main_box.get_text(separator=' ', strip=True)
                        content_text = raw_text[:300] + "...\n(スクレイピング抽出エラー)"
        elif site == 'gigazine':
            ggz_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(ggz_req, timeout=5) as ggz_res:
                soup = BeautifulSoup(ggz_res.read(), 'html.parser')
                body = soup.select_one('.cntimage')
                if body:
                    content_text = body.get_text('\n', strip=True)
                else:
                    content_text = desc if desc else "本文の取得に失敗しました。元のリンクからお読みください。"
        else:
            # Yahooの全文(段落のみ)スクレイピング
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
        
    return content_text

def filter_unique_and_sort(item_list, limit=50, sort=True):
    unique_urls = set()
    unique_items = []
    
    # 時間が取れる場合はソートする
    if sort:
        valid = [i for i in item_list if i['dt'] is not None]
        valid.sort(key=lambda x: x['dt'], reverse=True)
    else:
        valid = item_list
        
    for item in valid:
        if item['l'] not in unique_urls:
            unique_urls.add(item['l'])
            unique_items.append(item)
            if len(unique_items) >= limit:
                break
    return unique_items

def main():
    print("Fetching Yahoo RSS...")
    yahoo_items = fetch_yahoo_rss()
    yahoo_top_50 = filter_unique_and_sort(yahoo_items, 50, sort=True)
    
    print("Fetching Togetter Recent...")
    togetter_top_50 = filter_unique_and_sort(fetch_togetter_recent(50), 50, sort=False)
    
    print("Fetching GIGAZINE RSS...")
    gigazine_top_50 = filter_unique_and_sort(fetch_gigazine_rss(50), 50, sort=True)
    
    # Mixed sorting isn't perfect since togetter lacks exact dates, 
    # but we can interleave them or just append.
    all_selected = yahoo_top_50 + togetter_top_50 + gigazine_top_50
    
    final_data = []
    total = len(all_selected)
    for i, item in enumerate(all_selected):
        print(f"[{i+1}/{total}] Scraping: {item['t']}")
        content = scrape_full_text(item['l'], item['site'], item.get('desc', ''))
        
        # dtはJSONではSerializeできないので省く
        final_data.append({
            "t": item["t"],
            "l": item["l"],
            "d": item["d"],
            "cat": item["cat"],
            "site": item["site"],
            "pv": item["pv"],
            "time": item["time"],
            "c": content
        })
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))
        
    print(f"Done. Saved {len(final_data)} items.")

if __name__ == '__main__':
    main()
