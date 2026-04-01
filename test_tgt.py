import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json

req = urllib.request.Request("https://togetter.com/rss/hot", headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as res:
        xml_data = res.read()
    root = ET.fromstring(xml_data)
    items = root.findall('./channel/item')
    print(f"Total rss items: {len(items)}")
    
    if items:
        link = items[0].find('link').text
        print(f"Scraping: {link}")
        
        tgt_req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(tgt_req) as tgt_res:
            soup = BeautifulSoup(tgt_res.read(), 'html.parser')
            # Togetter uses specific class names for tweets, like div.tweet_box or blockquote.twitter-tweet
            tweets = soup.select('.list_tweet_box div.tweet, div.tweet_box, div.tweet')
            if not tweets:
                # sometimes it might use different DOM or lazy load?
                tweets = soup.select('.tweet_body')
            
            text = "\n\n".join(t.get_text(strip=True) for t in tweets[:5])
            print("--- Content ---")
            print(text[:500])
except Exception as e:
    print(f"Error: {e}")
