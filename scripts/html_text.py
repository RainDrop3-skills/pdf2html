"""HTML에서 화면에 보이는 글자만 뽑는다 (base64 이미지, style, script 제거).

임베드 이미지 때문에 HTML 줄이 너무 길어 Read 도구로 읽기 어려울 때,
또는 PDF 텍스트와 HTML 본문을 대조할 때 쓴다.

사용법:
    python -I html_text.py <html>                  # 전체 본문 텍스트
    python -I html_text.py <html> <시작 문구> [끝 문구]  # 시작~끝 구간만
시작 문구는 목차가 아니라 본문에만 있는 문구를 주는 게 좋다 (목차가 먼저 걸릴 수 있음).
"""
import html
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
if len(sys.argv) < 2:
    sys.exit(__doc__)

t = open(sys.argv[1], encoding="utf-8").read()
t = re.sub(r'src="data:[^"]+"', "", t)
t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S)
t = re.sub(r"<(h[1-4]|p|li|tr|div|blockquote|pre|caption|summary|figcaption)\b[^>]*>", "\n", t)
t = re.sub(r"<[^>]+>", "", t)
t = html.unescape(t)
t = re.sub(r"[ \t]+", " ", t)
t = re.sub(r"\n\s*\n+", "\n", t)

if len(sys.argv) >= 3:
    i = t.find(sys.argv[2])
    if i < 0:
        sys.exit("시작 문구를 찾지 못함")
    j = t.find(sys.argv[3], i + 1) if len(sys.argv) >= 4 else -1
    t = t[i:j] if j > 0 else t[i:]
print(t)
