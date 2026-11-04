"""Refresh the README from the website RSS feed, keeping existing content on errors."""
import html
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
FEED = "https://klepacek.xyz/rss.xml"


def update(readme, xml):
    root = ET.fromstring(xml)
    posts = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        url = urlparse(link)
        date = parsedate_to_datetime(item.findtext("pubDate") or "")
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        if date > datetime.now(timezone.utc):
            continue
        if not title or url.scheme != "https" or url.netloc != "klepacek.xyz" or not url.path.startswith("/blog/"):
            raise ValueError("Unexpected blog entry in website feed")
        posts.append((date, title, link))
    if not posts:
        raise ValueError("Feed contains no published posts; preserving README")
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one blog marker pair")
    before, remainder = readme.split(START)
    _, after = remainder.split(END)
    items = [f'  <li><a href="{html.escape(link, quote=True)}">{html.escape(title)}</a></li>'
             for _, title, link in sorted(posts, key=lambda post: post[0], reverse=True)[:5]]
    return before + START + "\n<ul>\n" + "\n".join(items) + "\n</ul>\n" + END + after


if __name__ == "__main__":
    # An optional local feed path allows checking the updater before deployment.
    if len(sys.argv) > 1:
        xml = Path(sys.argv[1]).read_bytes()
    else:
        request = Request(FEED, headers={"User-Agent": "klepacek-readme-blog/1.0"})
        with urlopen(request, timeout=30) as response:
            xml = response.read()
    path = Path("README.md")
    current = path.read_text(encoding="utf-8")
    updated = update(current, xml)
    if updated != current:
        path.write_text(updated, encoding="utf-8")
        print("Updated README blog posts.")
    else:
        print("README blog posts are already current.")
