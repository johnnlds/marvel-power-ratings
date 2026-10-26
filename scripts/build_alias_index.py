#!/usr/bin/env python3
"""Build a static search index of current and former aliases from Marvel Fandom."""
import concurrent.futures
import html
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DATA_URL = "https://raw.githubusercontent.com/sanand0/marvel-powers/master/marvel-powers-summary.json"
API_URL = "https://marvel.fandom.com/api.php"
OUT = Path("alias-index.json")
WORKERS = 5
MIN_REQUEST_INTERVAL = 0.16
_lock = threading.Lock()
_last_request = 0.0


def normalize(value):
    value = html.unescape(str(value or "")).lower()
    value = re.sub(r"[^a-z0-9]", "", value)
    return value


class InfoboxParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.row_depth = None
        self.source = None
        self.value_depth = None
        self.values = {"currentalias": [], "aliases": []}
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        source = (attrs.get("data-source") or "").lower()
        if source in self.values:
            self.source = source
            self.row_depth = self.depth + 1
            self.value_depth = None
            self.parts = []
        if self.source and ({"pi-data-value", "pi-item-value"} & classes):
            self.value_depth = self.depth + 1
        if self.source and self.value_depth is not None:
            if tag == "li" and self.depth >= self.value_depth:
                self.parts.append(" | ")
            elif tag == "br":
                self.parts.append(" | ")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth += 1

    def handle_data(self, data):
        if self.source and self.value_depth is not None and self.depth >= self.value_depth:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.source and self.value_depth is not None and self.depth == self.value_depth:
            self.value_depth = None
        if self.source and self.row_depth is not None and self.depth == self.row_depth:
            raw = re.sub(r"\s+", " ", "".join(self.parts)).strip(" ,|\t\r\n")
            raw = re.sub(r"\s*\|\s*", "|", raw)
            self.values[self.source].append(raw)
            self.source = None
            self.row_depth = None
            self.value_depth = None
            self.parts = []
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth = max(0, self.depth - 1)


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "MarvelPowerRatingsAliasIndex/1.0 (GitHub Actions)", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_page(character):
    global _last_request
    url = character.get("url") or ""
    try:
        parsed = urllib.parse.urlparse(url)
        parts = parsed.path.split("/wiki/", 1)
        if len(parts) != 2 or not parts[1]:
            return None
        slug = urllib.parse.unquote(parts[1])
        title = slug.replace("_", " ")
        api = API_URL + "?" + urllib.parse.urlencode({
            "action": "parse", "prop": "text", "format": "json", "page": title
        })
        for attempt in range(4):
            try:
                with _lock:
                    wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request)
                    if wait > 0:
                        time.sleep(wait)
                    _last_request = time.monotonic()
                payload = get_json(api)
                markup = payload.get("parse", {}).get("text", {}).get("*", "")
                if not markup:
                    return None
                parser = InfoboxParser()
                parser.feed(markup)
                current = next((x for x in parser.values["currentalias"] if x), "")
                former_raw = next((x for x in parser.values["aliases"] if x), "")
                former = [x.strip() for x in former_raw.split("|") if x.strip()]
                # Avoid treating a row label or the character's own title as a former alias.
                former = list(dict.fromkeys(x for x in former if normalize(x) not in {normalize(character.get("name")), normalize(title)}))
                return normalize(slug), {
                    "name": character.get("name", ""),
                    "currentAlias": current,
                    "formerAliases": former,
                }
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1.5 * (attempt + 1))
    except Exception as exc:
        print("Skipped:", character.get("name", url), "-", str(exc)[:180])
        return None


def main():
    print("Downloading character dataset…")
    rows = get_json(DATA_URL)
    characters = [row for row in rows if row.get("url")]
    print(f"Fetching aliases for {len(characters)} source pages…")
    aliases = {}
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_page, row) for row in characters]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                key, value = result
                aliases[key] = value
            completed += 1
            if completed % 100 == 0 or completed == len(futures):
                print(f"Processed {completed}/{len(futures)}; indexed {len(aliases)}")
    if len(aliases) < int(len(characters) * 0.70):
        raise RuntimeError(f"Only indexed {len(aliases)}/{len(characters)} pages; refusing to publish an incomplete alias index.")
    OUT.write_text(json.dumps({"version": 1, "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "aliases": aliases}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(aliases)} alias records to {OUT}")


if __name__ == "__main__":
    main()
