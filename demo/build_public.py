"""Build the GitHub Pages site from the approved multilingual design."""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"


class VisibleStrings(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.values: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden:
            for name, value in attrs:
                if name in {"aria-label", "alt", "title"} and value:
                    self.values.add(build.normalized(value))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.values.add(build.normalized(data))


def replace_once(source: str, pattern: str, replacement: str) -> str:
    result, count = re.subn(pattern, lambda match: match.expand(replacement), source, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected exactly one match: {pattern}")
    return result


def main() -> None:
    build.main()
    local_dir = ROOT.parent.parent / "local"
    preview = (local_dir if local_dir.is_dir() else ROOT.parent) / "TimeLineStamp-demo.html"
    page = preview.read_text(encoding="utf-8")
    page = page.replace("<title>TimeLineStamp — demo</title>", "<title>TimeLineStamp</title>", 1)
    page = replace_once(page, r'<div class="demo-note" role="note">.*?</div>',
        '<div class="demo-note" role="status"><strong id="live-label"></strong><span id="last-published"></span></div>')
    page = replace_once(page, r'<span class="node">.*?</span>', '<span class="node" id="record-node"></span>')
    page = replace_once(page, r'<div class="rail-foot">.*?</div>', '<div class="rail-foot" id="rail-status"></div>')
    page = replace_once(page, r'<span class="kicker">.*?</span>', '<span class="kicker" id="day-kicker"></span>')
    page = replace_once(page, r'(<section class="page-head".*?<h1 id="page-title">.*?</h1></div>)\s*<p>.*?</p>',
        r'\1<p id="page-intro"></p>')
    page = replace_once(page, r'<span class="lock">.*?</span>', '<span class="lock" id="lock-status"></span>')
    page = replace_once(page, r'(<div class="instrument-top">)<span>.*?</span>',
        r'\1<span id="instrument-label"></span>')
    page = replace_once(page, r'(<div class="display-label"><span>.*?</span>)<span>.*?</span>',
        r'\1<span id="display-day"></span>')
    page = replace_once(page, r'<div class="digits" role="img".*?</div>',
        '<div class="digits" id="meter" role="img" aria-label=""></div>')
    page = replace_once(page, r'(<div class="display-note"><span>.*?</span>)<span class="partial">.*?</span>',
        r'\1<span class="partial" id="quality"></span>')
    page = replace_once(page, r'(<div class="display-note">)<span>.*?</span>',
        r'\1<span id="number-note"></span>')
    page = replace_once(page, r'(<div class="signature">\s*<div><span class="micro">.*?</span>)<strong>.*?</strong>',
        r'\1<strong id="digest"></strong>')
    page = replace_once(page, r'(<div class="signature-graph"><svg.*?<g[^>]*>).*?(</g>)', r'\1\2')
    page = replace_once(page, r'<div class="facts".*?(?=\s*<section class="section theory")',
        '<div class="facts" aria-label="Period details">'
        '<div class="fact"><span class="micro" id="period-label"></span><strong id="period"></strong><small id="period-note"></small></div>'
        '<div class="fact"><span class="micro" id="next-lock-label"></span><strong id="next-lock"></strong><small id="next-lock-note"></small></div>'
        '<div class="fact"><span class="micro" id="quantum-label"></span><strong id="quantum-count"></strong><small id="quantum-note"></small></div>'
        '</div>')
    page = replace_once(page, r'(<section class="section" id="sources".*?<div class="section-head">.*?</h2></div>)<p>.*?</p>',
        r'\1<p id="streams-description"></p>')
    page = replace_once(page, r'(<div class="streams">).*?(</div>\s*</section>\s*<section class="section" id="archive")',
        r'\1<div id="streams"></div>\2')
    page = replace_once(page, r'(<div class="record-table"><table><thead>.*?</thead><tbody>).*?(</tbody>)',
        r'\1\2')
    page = page.replace('<tbody></tbody>', '<tbody id="history"></tbody>', 1)
    page = replace_once(page, r'<div class="table-foot">.*?</div>',
        '<div class="table-foot"><span id="archive-count"></span><span id="archive-note"></span></div>')
    page = replace_once(page, r'<p class="library-endnote">.*?</p>',
        '<p class="library-endnote" id="library-endnote"></p>')
    page = replace_once(page, r'<footer class="footer"><span>.*?</span>',
        '<footer class="footer"><span>TIMELINESTAMP / V1</span>')

    # The mockup's mail template embeds a fictional day. The public link is
    # recalculated from the current record by app.js after each language change.
    mail = {lang: {
        "discrepancy": build.mailto("TimeLineStamp — discrepancy"),
        "time-machine": build.mailto_catalog()[lang]["time-machine"],
    } for lang in ("en", "ru", "zh")}
    page = replace_once(page, r'(<a class="contact-button" data-mailto="discrepancy" href=").*?("\>)',
        r'\1' + html.escape(mail["en"]["discrepancy"], quote=True) + r'\2')
    page = replace_once(page, r'const mailto = \{.*?\};\n  const storageKey',
        'const mailto = ' + json.dumps(mail, ensure_ascii=False) + ';\n  const storageKey')
    page = page.replace('document.title = selected === "en" ? title : catalog[title][selected];',
                        'document.title = "TimeLineStamp";', 1)
    page = page.replace('const storageKey = "timelinestamp-demo-language";',
                        'const storageKey = "timelinestamp-language";', 1)
    visible = VisibleStrings()
    visible.feed(page)
    catalog_match = re.search(r'const catalog = (\{.*?\});\n  const mailto', page, flags=re.S)
    if not catalog_match:
        raise ValueError("Translation catalog missing")
    catalog = json.loads(catalog_match.group(1))
    public_catalog = {key: value for key, value in catalog.items() if key in visible.values}
    page = page[:catalog_match.start(1)] + json.dumps(public_catalog, ensure_ascii=False).replace("</", "<\\/") + page[catalog_match.end(1):]
    page = page.replace('</body>', '  <script src="./app.js?v=initial-1" defer></script>\n</body>', 1)
    if "__" in page and re.search(r"__[A-Z_]+__", page):
        raise ValueError("Unresolved template marker")
    DOCS.mkdir(exist_ok=True)
    destination = DOCS / "index.html"
    destination.write_text(page, encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
