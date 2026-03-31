import urllib.request
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

url = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as res:
    xml_data = res.read()
root = ET.fromstring(xml_data)

item = root.find('./channel/item')
link = item.find('link').text
print(f"Scraping link: {link}")

try:
    art_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(art_req) as art_res:
        html = art_res.read()
        soup = BeautifulSoup(html, 'html.parser')

        # Check if it's a pickup page
        if 'news.yahoo.co.jp/pickup/' in link:
            # Need to find the actual article link
            # The button usually says "続きを読む" or "記事全文を読む"
            # In Yahoo it's often an <a> tag with href containing "articles/"
            next_link_tag = soup.find('a', href=lambda h: h and 'news.yahoo.co.jp/articles/' in h)
            if next_link_tag:
                actual_link = next_link_tag['href']
                print(f"Found actual article link: {actual_link}")
                
                # Fetch actual article
                art_req2 = urllib.request.Request(actual_link, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(art_req2) as art_res2:
                    soup2 = BeautifulSoup(art_res2.read(), 'html.parser')
                    
                    # paragraphs
                    # The class name is dynamic often, so finding by div.article_body or something similar
                    # Sometimes it's just 'div' with class 'highLightSearchTarget' or 'p' tags inside some container
                    paragraphs = soup2.select('div.article_body p.highLightSearchTarget, div.article_body p, .article_body p, p.highLightSearchTarget')
                    if paragraphs:
                        print("\n--- Parsed Content ---")
                        print("\n\n".join(p.get_text(strip=True) for p in paragraphs))
                    else:
                        print("Article select failed.")
                        for p in soup2.find_all('p'):
                            print(p)
            else:
                print("Could not find article redirect link on pickup page.")
        else:
            # Direct article
            paragraphs = soup.select('div.article_body p.highLightSearchTarget, div.article_body p')
            if paragraphs:
                print("\n--- Parsed Content ---")
                print("\n\n".join(p.get_text(strip=True) for p in paragraphs))
except Exception as e:
    print(f"Exception: {e}")
