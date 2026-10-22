"""Build the standalone, offline TimeLineStamp design mockup."""

import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parent
DEMO_HASH = "83bf42813c6a90341a85cd8d5e4f59364fd985cf0590bbec5f67b96b7b2aec6e"
CONTACT_EMAIL = "rift.research@outlook.com"
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def normalized(value: str) -> str:
    return " ".join(html.unescape(value).split())


def translate_template(template: str, translations: dict[str, list[str]]) -> str:
    by_source = {normalized(key): pair for key, pair in translations.items()}

    def replace_text(match: re.Match[str]) -> str:
        raw = match.group(1)
        source = normalized(raw)
        if not CYRILLIC.search(source):
            return match.group(0)
        if source not in by_source:
            raise ValueError(f"Missing text translation: {source}")
        leading = re.match(r"\s*", raw).group()
        trailing = re.search(r"\s*$", raw).group()
        return ">" + leading + html.escape(by_source[source][0], quote=False) + trailing + "<"

    template = re.sub(r">([^<>]+)<", replace_text, template)

    def replace_attribute(match: re.Match[str]) -> str:
        name, raw = match.groups()
        source = normalized(raw)
        if not CYRILLIC.search(source):
            return match.group(0)
        if source not in by_source:
            raise ValueError(f"Missing attribute translation: {source}")
        return f'{name}="{html.escape(by_source[source][0], quote=True)}"'

    template = re.sub(r'(aria-label|alt|title)="([^"]+)"', replace_attribute, template)
    return template.replace('<html lang="ru">', '<html lang="en">', 1)


def mailto(subject: str, body: str = "") -> str:
    query = {"subject": subject}
    if body:
        query["body"] = body
    return f"mailto:{CONTACT_EMAIL}?" + urlencode(query)


def mailto_catalog() -> dict[str, dict[str, str]]:
    return {
        "en": {
            "discrepancy": mailto("TimeLineStamp — discrepancy for 2026-10-21", "UTC date: 2026-10-21\nNumber I remember: \nNumber shown now: 1.482731\nWhen I noticed the difference: "),
            "time-machine": mailto("TimeLineStamp — time machine"),
        },
        "ru": {
            "discrepancy": mailto("TimeLineStamp — расхождение за 2026-10-21", "Дата UTC: 2026-10-21\nЧисло, которое я помню: \nЧисло на странице сейчас: 1.482731\nКогда заметил расхождение: "),
            "time-machine": mailto("TimeLineStamp — машина времени"),
        },
        "zh": {
            "discrepancy": mailto("TimeLineStamp — 2026-10-21 读数差异", "UTC 日期：2026-10-21\n我记得的数字：\n页面当前显示的数字：1.482731\n发现差异的时间："),
            "time-machine": mailto("TimeLineStamp — 时间机器"),
        },
    }


def main() -> None:
    bars = []
    for index, digit in enumerate(DEMO_HASH):
        height = 7 + int(digit, 16) * 2.1
        x = 2 + index * 4
        bars.append(f'<line x1="{x}" y1="{43 - height:.1f}" x2="{x}" y2="43"/>')
    template = (ROOT / "v4-template.html").read_text(encoding="utf-8")
    preview_redirect = '  <meta http-equiv="refresh" content="0; url=../../local/TimeLineStamp-demo.html">\n'
    if template.count(preview_redirect) != 1:
        raise ValueError("The source template must redirect direct browser visits to the built demo")
    template = template.replace(preview_redirect, "", 1)
    translations = json.loads((ROOT / "translations.json").read_text(encoding="utf-8"))
    reverse: dict[str, dict[str, str]] = {}
    for source, (english, chinese) in translations.items():
        if english in reverse and reverse[english]["ru"] != source:
            raise ValueError(f"Duplicate English translation: {english}")
        reverse[english] = {"ru": source, "zh": chinese}
    result = translate_template(template, translations)
    result = result.replace("__CSS__", (ROOT / "style-v4.css").read_text(encoding="utf-8").rstrip())
    result = result.replace("__HASH_BARS__", "".join(bars))
    result = result.replace("__CONTACT_EMAIL__", html.escape(CONTACT_EMAIL))
    mails = mailto_catalog()
    result = result.replace("__MAIL_DISCREPANCY__", html.escape(mails["en"]["discrepancy"], quote=True))
    result = result.replace("__MAIL_TIME_MACHINE__", html.escape(mails["en"]["time-machine"], quote=True))
    script = (ROOT / "i18n.js").read_text(encoding="utf-8")
    script = script.replace("__CATALOG__", json.dumps(reverse, ensure_ascii=False).replace("</", "<\\/"))
    script = script.replace("__MAIL_CATALOG__", json.dumps(mails, ensure_ascii=False))
    result = result.replace("__I18N_SCRIPT__", script.rstrip())
    for marker, filename in {
        "__IMG_NIST__": "nist-quantum-lab.jpg",
        "__IMG_SPACECRAFT__": "dscovr-cleanroom.jpg",
        "__IMG_EARTH__": "dscovr-earth.jpg",
    }.items():
        photo = base64.b64encode((ROOT / "assets" / filename).read_bytes()).decode("ascii")
        result = result.replace(marker, f"data:image/jpeg;base64,{photo}")
    assert not any(marker in result for marker in ("__CSS__", "__HASH_BARS__", "__IMG_NIST__", "__IMG_SPACECRAFT__", "__IMG_EARTH__", "__I18N_SCRIPT__", "__CONTACT_EMAIL__", "__MAIL_DISCREPANCY__", "__MAIL_TIME_MACHINE__"))
    local_dir = ROOT.parent.parent / "local"
    destination = (local_dir if local_dir.is_dir() else ROOT.parent) / "TimeLineStamp-demo.html"
    destination.write_text(result, encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
