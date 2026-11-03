#!/usr/bin/env python3
"""Minimal Markdown to HTML converter for the learning documents (headings, lists, bold, italic)."""
import argparse
import html
import re
import sys

CSS = """
@page { size: A4; margin: 20mm 18mm; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 22pt; margin: 0 0 8pt; }
h2 { font-size: 15pt; margin: 22pt 0 6pt; border-bottom: 1px solid #ccc; padding-bottom: 3pt; break-after: avoid; }
h3 { font-size: 12.5pt; margin: 16pt 0 5pt; break-after: avoid; }
p { margin: 0 0 7pt; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def convert(md: str) -> str:
    out, para, list_kind = [], [], None

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append(f"</{list_kind}>")
            list_kind = None

    for raw in md.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            close_list()
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        bullet = re.match(r"^-\s+(.*)$", line)
        number = re.match(r"^\d+\.\s+(.*)$", line)
        if heading:
            flush_para()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif bullet or number:
            flush_para()
            kind = "ul" if bullet else "ol"
            if list_kind != kind:
                close_list()
                out.append(f"<{kind}>")
                list_kind = kind
            out.append("<li>" + inline((bullet or number).group(1)) + "</li>")
        else:
            close_list()
            para.append(line.strip())
    flush_para()
    close_list()
    return "\n".join(out)


COVER_CSS = """
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; text-align: center; break-after: page; }
.cover .label { font-size: 11pt; letter-spacing: 3pt; text-transform: uppercase; color: #666; margin-bottom: 40pt; }
.cover .title { font-size: 40pt; font-weight: 700; line-height: 1.15; margin: 0 0 14pt; }
.cover .subtitle { font-size: 16pt; color: #444; margin: 0 0 56pt; }
.cover .author { font-size: 18pt; margin: 0 0 6pt; }
.cover .meta { font-size: 11pt; color: #555; margin: 0 0 4pt; }
.cover .note { margin-top: 64pt; font-size: 10pt; color: #666; border-top: 1px solid #ccc; padding-top: 12pt; }
"""


def cover(args: argparse.Namespace, md: str) -> str:
    reading_text = md.split("## 9. Selbsttest")[0]
    words_text = f"{len(md.split()):,}".replace(",", ".")
    minutes = round(len(reading_text.split()) / 120)
    lines = [f'<div class="meta">{html.escape(args.publisher)}</div>' if args.publisher else ""]
    lines.append(f'<div class="meta">{html.escape(args.edition)}</div>' if args.edition else "")
    lines.append(f'<div class="meta">ISBN {html.escape(args.isbn)}</div>' if args.isbn else "")
    return (
        '<section class="cover">'
        f'<div class="label">{html.escape(args.label)}</div>'
        f'<div class="title">{html.escape(args.title)}</div>'
        f'<div class="subtitle">{html.escape(args.subtitle)}</div>'
        f'<div class="author">{html.escape(args.author)}</div>'
        + "".join(lines)
        + f'<div class="note">{html.escape(args.note)}<br>'
        + html.escape(args.stats.format(date=args.date, words=words_text, minutes=minutes))
        + "</div></section>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--author", required=True)
    parser.add_argument("--publisher", default="")
    parser.add_argument("--edition", default="")
    parser.add_argument("--isbn", default="")
    parser.add_argument("--date", required=True)
    parser.add_argument("--label", default="Zusammenfassung · Lerndokument")
    parser.add_argument("--note", default="Eigene Zusammenfassung zum Lernen, kein Ersatz für das Buch.")
    parser.add_argument("--stats", default="Erstellt am {date} · {words} Wörter · ca. {minutes} Minuten Lesezeit")
    args = parser.parse_args()
    with open(args.src, encoding="utf-8") as f:
        md = f.read()
    body = cover(args, md) + convert(md)
    page = (
        f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>{html.escape(args.title)}</title>'
        f"<style>{CSS}{COVER_CSS}</style></head><body>{body}</body></html>"
    )
    with open(args.dst, "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
