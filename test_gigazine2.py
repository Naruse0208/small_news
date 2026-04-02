import urllib.request
from bs4 import BeautifulSoup

url = "https://gigazine.net/news/20260402-apple-randomly-closes-bug-reports-verify-unfixed/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as art_res:
    soup = BeautifulSoup(art_res.read(), 'html.parser')
    
    # Try different selectors
    print("cntimage:", soup.select_one('.cntimage') is not None)
    print("article:", soup.select_one('article') is not None)
    print("div.preface:", soup.select_one('div.preface') is not None)
    
    body = soup.select_one('.cntimage')
    if body:
        # print first 500 chars of text
        print(body.get_text('\n', strip=True)[:500])
