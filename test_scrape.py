import urllib.request
import re
from html.parser import HTMLParser

class YahooNewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_article_body = False
        self.text_content = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for attr, val in attrs:
                if attr == "class" and "article_body" in val:
                    self.in_article_body = True
                    break

    def handle_endtag(self, tag):
        # We'll just grab everything inside the first div.article_body
        pass

    def handle_data(self, data):
        if self.in_article_body:
            # Append if not purely whitespace
            if data.strip():
                self.text_content.append(data.strip())

def scrape_yahoo(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as res:
            html = res.read().decode('utf-8', errors='ignore')
            
            # Use regex to find article body content roughly
            import re
            # Extract content from <p class="highLightSearchTarget"> since it holds paragraph bodies, or .article_body elements
            # A simple regex for taking content roughly:
            match = re.search(r'<div[^>]*class="[^"]*article_body[^"]*"[^>]*>(.*?)</div>\s*<(!--|div|script)', html, re.DOTALL | re.IGNORECASE)
            
            if match:
                content = match.group(1)
                # Strip all inner tags
                text = re.sub(r'<[^>]+>', '', content)
                # Decode HTML entities
                import html as htmllib
                text = htmllib.unescape(text)
                return text.strip()
            else:
                return "本文を取得できませんでした。"
    except Exception as e:
        return f"エラー: {e}"

if __name__ == "__main__":
    url = "https://news.yahoo.co.jp/articles/86e96a4ce0ce24de13a37afcadb9442a842f2ed1" # example article
    print(scrape_yahoo(url))
