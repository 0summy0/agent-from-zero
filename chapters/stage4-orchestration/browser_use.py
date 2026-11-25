import json
from html.parser import HTMLParser
from urllib.parse import urlsplit

CHAPTER_ID = "4.2-browser-use"

HOME_URL = "local://home"
DOCS_URL = "local://docs"
CONTACT_URL = "local://contact"

LOCAL_PAGES = {
    HOME_URL: """<!doctype html>
<html lang="en">
<head><title>Agent From Zero - Home</title></head>
<body>
  <nav><a href="local://docs">Documentation</a> | <a href="local://contact">Contact</a></nav>
  <main><h1>Agent From Zero</h1><p>Learn agents with small, local examples.</p></main>
  <script>hiddenScript = true;</script>
</body>
</html>""",
    DOCS_URL: """<!doctype html>
<html lang="en">
<head><title>Agent From Zero - Documentation</title></head>
<body>
  <nav><a href="local://home">Home</a> | <a href="local://contact">Contact</a></nav>
  <main>
    <h1>Browser agent documentation</h1>
    <p>Observe the page, decide the next action, and act with a tool.</p>
    <p>Prefer visible link text over brittle generated selectors.</p>
  </main>
</body>
</html>""",
    CONTACT_URL: """<!doctype html>
<html lang="en">
<head><title>Agent From Zero - Contact</title></head>
<body>
  <nav><a href="local://home">Home</a> | <a href="local://docs">Documentation</a></nav>
  <main><h1>Contact</h1><p>This local demo does not send messages or use the network.</p></main>
</body>
</html>""",
}

_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
    "td", "th", "tr", "ul",
}
_NON_VISIBLE_TAGS = {"script", "style", "template", "noscript"}
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def normalize_text(text):
    return " ".join(text.split())


class PageParser(HTMLParser):
    """Extract a title, visible body text, and links from a small HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.links = []
        self._in_title = False
        self._in_body = False
        self._hidden_tags = []
        self._anchor_text = None
        self._anchor_href = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "body":
            self._in_body = True
        if tag == "title":
            self._in_title = True
        if tag not in _VOID_TAGS and (tag in _NON_VISIBLE_TAGS or "hidden" in attributes):
            self._hidden_tags.append(tag)
        if tag in _BLOCK_TAGS:
            self._append_visible(" ")
        if tag == "a" and self._anchor_text is None:
            self._anchor_text = []
            self._anchor_href = attributes.get("href")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        # HTML ignores the self-closing slash on non-void elements such as div.
        if tag.lower() in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "a" and self._anchor_text is not None:
            text = normalize_text("".join(self._anchor_text))
            if text and self._anchor_href is not None:
                self.links.append({"text": text, "href": self._anchor_href})
            self._anchor_text = None
            self._anchor_href = None
        if tag in _BLOCK_TAGS:
            self._append_visible(" ")
        if tag == "title":
            self._in_title = False
        if self._hidden_tags and tag == self._hidden_tags[-1]:
            self._hidden_tags.pop()
        if tag == "body":
            self._in_body = False

    def _append_visible(self, text):
        if self._in_body and not self._hidden_tags:
            self.text_parts.append(text)
            if self._anchor_text is not None:
                self._anchor_text.append(text)

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        else:
            self._append_visible(data)

    def result(self):
        return {
            "title": normalize_text("".join(self.title_parts)),
            "text": normalize_text("".join(self.text_parts)),
            "links": list(self.links),
        }


def parse_html(html):
    """Parse one in-memory HTML string without executing scripts or loading assets."""
    if not isinstance(html, str):
        raise ValueError("html must be a string")
    parser = PageParser()
    parser.feed(html)
    parser.close()
    return parser.result()


class BrowserTool:
    """A deterministic browser-shaped tool backed only by a fixed in-memory page map."""

    def __init__(self, pages=None):
        source = LOCAL_PAGES if pages is None else pages
        if not isinstance(source, dict):
            raise ValueError("pages must be a dictionary of local URLs to HTML")
        self._pages = dict(source)
        self._current_url = None
        self._page = None

    def open_page(self, url):
        """Open an exact page in the allowlist; no URL is fetched."""
        if not isinstance(url, str):
            raise ValueError("url must be a string")
        if url not in self._pages:
            raise ValueError(f"unknown local page: {url}")
        parsed = urlsplit(url)
        if parsed.scheme != "local" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("only absolute local:// page URLs without query or fragment are allowed")
        self._page = parse_html(self._pages[url])
        self._current_url = url
        return {"url": self._current_url, **self._page}

    def click_link(self, text):
        """Follow a link by its complete, whitespace-normalized visible text."""
        if self._page is None:
            raise ValueError("open a page before clicking a link")
        target = normalize_text(text) if isinstance(text, str) else ""
        if not target:
            raise ValueError("link text must be a non-empty string")
        matches = [
            link for link in self._page["links"]
            if normalize_text(link["text"]).casefold() == target.casefold()
        ]
        if not matches:
            raise ValueError(f"unknown link text: {text}")
        if len(matches) != 1:
            raise ValueError(f"ambiguous link text: {text}")
        return self.open_page(matches[0]["href"])

    def current_url(self):
        return self._current_url


def run_minimal_path():
    browser = BrowserTool()
    browser.open_page(HOME_URL)
    page = browser.click_link("Documentation")
    return {
        "chapter": CHAPTER_ID,
        "url": browser.current_url(),
        "title": page["title"],
        "text_summary": page["text"][:160],
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
