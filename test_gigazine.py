import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re

url = "https://gigazine.net/news/rss_2.0/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as res:
        xml_data = res.read()
    root = ET.fromstring(xml_data)
    for item in root.findall('./channel/item')[:3]:
        title = item.find('title').text
        link = item.find('link').text
        print(title, link)
        
        art_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(art_req, timeout=10) as art_res:
            soup = BeautifulSoup(art_res.read(), 'html.parser')
            # Typical gigazine article body
            body = soup.select_one('.cntimage') or soup.select_one('article')
            if body:
                text = body.get_text('\n', strip=True)
                print(text[:200])
            else:
                print("Could not find article body")
        print("-" * 50)
except Exception as e:
    print(f"Error: {e}")
