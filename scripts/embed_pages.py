"""원본 슬라이드 임베드 도구.

HTML 안의 <img data-pdf="파일.pdf" data-page="N" ...> 태그를 찾아
해당 PDF 페이지를 PNG로 렌더링한 뒤 base64 data URI(src)로 넣는다.
이미 src가 들어간 태그는 건드리지 않으므로 여러 번 실행해도 안전하다.

사용법: python -I embed_pages.py "<html 경로>" "<PDF 폴더>" [dpi=90]
"""
import base64
import html
import os
import re
import subprocess
import sys
import tempfile

html_path, pdf_dir = sys.argv[1], sys.argv[2]
dpi = sys.argv[3] if len(sys.argv) > 3 else "90"

with open(html_path, encoding="utf-8") as f:
    text = f.read()

pattern = re.compile(r'<img\s+data-pdf="([^"]+)"\s+data-page="(\d+)"([^>]*)>')
cache = {}


def render(pdf, page):
    key = (pdf, page)
    if key not in cache:
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "p")
            subprocess.run(
                ["pdftoppm", "-png", "-r", dpi, "-f", page, "-l", page, "-singlefile",
                 os.path.join(pdf_dir, pdf), out],
                check=True,
            )
            with open(out + ".png", "rb") as img:
                data = img.read()
        cache[key] = "data:image/png;base64," + base64.b64encode(data).decode()
    return cache[key]


def replace(m):
    pdf_attr, page, rest = m.group(1), m.group(2), m.group(3)
    uri = render(html.unescape(pdf_attr), page)
    return f'<img src="{uri}" data-pdf="{pdf_attr}" data-page="{page}" loading="lazy"{rest}>'


new_text, n = pattern.subn(replace, text)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_text)
print(f"embedded {n} image(s); file size = {os.path.getsize(html_path) / 1024:.0f} KB")
