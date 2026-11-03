"""pdf2html 결과 HTML 검수.

사용법:
    python -I check.py <html> <약칭>=<PDF 경로 또는 페이지 수> [...] [--everytime]

예:
    python -I check.py "05. SQL - 설명.html" 05A="05. A. join.pdf" 05B="05. B. sub.pdf" --everytime

검사 항목:
    - 태그 짝, 중복 id, 깨진 #링크
    - 변환 안 된 <img data-pdf> 태그, 외부 리소스 참조, 템플릿 자리표시자 잔존
    - 원본 페이지 대응표(#coverage)가 PDF마다 모든 페이지를 덮는지
    - h2/h3 출처 태그(.src) 누락
    - --everytime: 📌 배지와 #everytime 표가 서로 맞는지 / 옵션 없으면 에타 표시가 없어야 함
마지막 줄에 RESULT: OK 또는 RESULT: FAIL을 출력하고, FAIL이면 종료 코드 1.
"""
import re
import subprocess
import sys
from collections import defaultdict
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8")

argv = sys.argv[1:]
everytime = "--everytime" in argv
argv = [a for a in argv if a != "--everytime"]
if not argv:
    sys.exit(__doc__)
path = argv[0]

expected = {}
for arg in argv[1:]:
    key, val = arg.split("=", 1)
    if val.isdigit():
        expected[key] = int(val)
        continue
    out = subprocess.run(["pdfinfo", val], capture_output=True).stdout.decode("utf-8", "replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        sys.exit(f"pdfinfo로 페이지 수를 읽지 못함: {val}")
    expected[key] = int(m.group(1))

text = open(path, encoding="utf-8").read()
# base64 이미지 데이터를 뺀 본문 (자리표시자 같은 문자열 검사가 이미지 데이터에 우연히 걸리지 않게)
plain = re.sub(r'src="data:[^"]+"', 'src=""', text)
fails, warns = [], []


class P(HTMLParser):
    VOID = {"br", "img", "meta", "link", "hr", "input", "source", "col", "wbr", "area", "base", "embed", "track"}

    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.stack, self.errors = set(), [], [], []

    def _id(self, attrs):
        a = dict(attrs)
        if "id" in a:
            if a["id"] in self.ids:
                self.errors.append(f"중복 id {a['id']}")
            self.ids.add(a["id"])
        return a

    def handle_starttag(self, tag, attrs):
        a = self._id(attrs)
        if tag == "a" and a.get("href", "").startswith("#"):
            self.hrefs.append(a["href"][1:])
        if tag not in self.VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        self._id(attrs)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if i != len(self.stack) - 1:
                    self.errors.append(f"닫히지 않은 {[t for t, _ in self.stack[i + 1:]]} (</{tag}> 앞, 줄 {self.getpos()[0]})")
                del self.stack[i:]
                return
        self.errors.append(f"짝 없는 </{tag}> (줄 {self.getpos()[0]})")


p = P()
p.feed(text)
size_mb = len(text.encode("utf-8")) / 1024 / 1024
print(f"크기: {size_mb:.2f} MB")
if size_mb > 15:
    warns.append(f"파일이 큼 ({size_mb:.1f} MB): 임베드 이미지 수나 dpi를 줄일 것")

if p.errors or p.stack:
    fails.append(f"태그 문제: {p.errors[:8]} / 끝까지 열린 태그: {[t for t, _ in p.stack][:8]}")

missing = sorted({h for h in p.hrefs if h and h not in p.ids})
if missing:
    fails.append(f"깨진 #링크: {missing[:15]}")

n_unconv = len(re.findall(r"<img\s+data-pdf=", text))
n_img = len(re.findall(r'src="data:image/', text))
if n_unconv:
    fails.append(f"변환 안 된 원본 슬라이드 이미지 {n_unconv}개: embed_pages.py를 실행할 것")
if n_img > 15:
    warns.append(f"임베드 이미지 {n_img}장 (권장 15장 이하)")

ext_src = re.findall(r'<(?:img|script|link|iframe|source)\b[^>]*?(?:src|href)="(https?://[^"]+)"', text)
if ext_src:
    fails.append(f"외부 리소스 참조 (오프라인에서 깨짐): {ext_src[:5]}")
ext_links = re.findall(r'<a\b[^>]*href="(https?://[^"]+)"', text)
if ext_links:
    warns.append(f"외부 하이퍼링크 {len(ext_links)}개 (PDF에 있는 링크인지 확인): {ext_links[:3]}")

placeholders = ["챕터 제목", "과목명 · ", "0NA", "파일명.pdf", "PDF에 있는 핵심 내용.", "@@NEXT@@", "에타-매핑.md"]
left = [ph for ph in placeholders if ph in plain]
if left:
    fails.append(f"템플릿 자리표시자가 남아 있음: {left}")

# h2/h3 출처 태그
no_src = []
for m in re.finditer(r'<h([23])\b([^>]*)>(.*?)</h\1>', text, re.S):
    attrs, inner = m.group(2), m.group(3)
    hid = re.search(r'id="([^"]+)"', attrs)
    if hid and hid.group(1) in ("coverage", "everytime"):
        continue
    if 'class="src"' not in inner:
        no_src.append(re.sub(r"<[^>]+>", "", inner).strip()[:30])
if no_src:
    warns.append(f"출처 태그(.src) 없는 제목 {len(no_src)}개: {no_src[:6]}")

# 원본 페이지 대응표
cov_at = text.find('id="coverage"')
if cov_at < 0:
    fails.append("원본 페이지 대응표(#coverage)가 없음")
else:
    cov = text[cov_at:]
    rows = re.findall(r"<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>", cov)
    pages = defaultdict(set)
    for f, pg in rows:
        for part in re.split(r"[,\s]+", pg.strip()):
            m = re.match(r"^(\d+)(?:[–~-](\d+))?$", part)
            if m:
                a, b = int(m.group(1)), int(m.group(2) or m.group(1))
                pages[f.strip()].update(range(a, b + 1))
    for k, n in expected.items():
        got = pages.get(k, set())
        miss = sorted(set(range(1, n + 1)) - got)
        extra = sorted(x for x in got if x > n)
        print(f"대응표 {k}: {len(got & set(range(1, n + 1)))}/{n}" + (f" 빠진 쪽 {miss}" if miss else " OK"))
        if miss:
            fails.append(f"대응표 {k} 누락 페이지: {miss}")
        if extra:
            fails.append(f"대응표 {k}에 없는 페이지 번호: {extra}")
    unknown = set(pages) - set(expected)
    if expected and unknown:
        warns.append(f"대응표에 인자로 주지 않은 파일 약칭: {sorted(unknown)}")

# 에타 표시
badge_qs = re.findall(r'class="eta"[^>]*>[^<]*?📌[^<]*?</span>', text)
eta_nums = set()
for b in badge_qs:
    eta_nums.update(re.findall(r"Q(\d+)", b))
has_eta_markup = bool(badge_qs) or 'class="box eta"' in text or 'id="everytime"' in text
if everytime:
    if not badge_qs:
        fails.append("--everytime인데 📌 에타 배지가 하나도 없음 (관련 문제가 정말 없으면 #everytime 표에 그렇게 적고 이 항목은 무시)")
    ev_at = text.find('id="everytime"')
    if ev_at < 0:
        fails.append("--everytime인데 '에타 기출 연결'(#everytime) 섹션이 없음")
    else:
        ev = text[ev_at:cov_at if cov_at > ev_at else None]
        table_nums = set(re.findall(r"<td>\s*Q(\d+)\s*</td>", ev))
        lost = sorted(eta_nums - table_nums, key=int)
        if lost:
            fails.append(f"본문 배지에는 있는데 #everytime 표에 없는 문제: {['Q' + q for q in lost]}")
        print(f"에타: 배지 {len(badge_qs)}개, 본문에 연결된 문제 {sorted(eta_nums, key=int)}, 표의 문제 {sorted(table_nums, key=int)}")
elif has_eta_markup:
    fails.append("--everytime 옵션이 아닌데 에타 표시(.eta / .box.eta / #everytime)가 들어 있음")

counts = {name: text.count(f'class="{cls}"') for name, cls in [
    ("원문 인용", "quote"), ("출처 태그", "src"), ("보충 설명", "box extra"),
    ("오류 의심", "box suspect"), ("퀴즈", "quiz")]}
print(" · ".join(f"{k} {v}" for k, v in counts.items()) + f" · 임베드 이미지 {n_img}")
for w in warns:
    print("WARN:", w)
for f in fails:
    print("FAIL:", f)
print("RESULT:", "FAIL" if fails else "OK")
sys.exit(1 if fails else 0)
