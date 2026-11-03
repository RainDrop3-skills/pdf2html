"""완성한 HTML을 헤드리스 Edge/Chrome으로 렌더링해 PNG로 저장한다 (눈으로 레이아웃 확인용).

사용법:
    python -I screenshot.py <html> <out.png> [--width 1280] [--height 2400] [--dark]

    --width 390  : 휴대폰 폭 확인
    --dark       : 다크 모드(prefers-color-scheme: dark)로 렌더링
    <html> 뒤에 #id를 붙이면 그 위치로 스크롤된 화면을 찍는다 (예: "file.html#b-3")

사용자의 브라우저 프로필과 섞이지 않도록 임시 프로필 폴더를 쓴다.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_browser():
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("Edge/Chrome을 찾지 못함")


ap = argparse.ArgumentParser()
ap.add_argument("html")
ap.add_argument("out")
ap.add_argument("--width", type=int, default=1280)
ap.add_argument("--height", type=int, default=2400)
ap.add_argument("--dark", action="store_true")
a = ap.parse_args()

file_part, _, frag = a.html.partition("#")
url = Path(file_part).resolve().as_uri() + (f"#{frag}" if frag else "")
out = Path(a.out).resolve()

# 헤드리스 창은 폭이 약 500px보다 좁아지지 않는다. 그래서 좁은 폭은
# 정확한 폭의 iframe에 페이지를 넣어 찍고, 남는 오른쪽을 잘라 낸다.
# #id로 스크롤한 화면도 창에서 바로 찍으면 빈 화면이 나오므로 같은 방식을 쓴다.
MIN_WINDOW = 520
narrow = a.width < MIN_WINDOW or bool(frag)

with tempfile.TemporaryDirectory() as tmp:
    target = url
    win_w = a.width
    if narrow:
        wrap = Path(tmp) / "wrap.html"
        wrap.write_text(
            f'<!doctype html><meta charset="utf-8"><body style="margin:0;background:#808080">'
            f'<iframe src="{url}" style="border:0;display:block;width:{a.width}px;height:{a.height}px"></iframe>',
            encoding="utf-8")
        target = wrap.as_uri()
        win_w = max(a.width, MIN_WINDOW)
    cmd = [find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           f"--user-data-dir={Path(tmp) / 'profile'}", f"--window-size={win_w},{a.height}", f"--screenshot={out}"]
    if a.dark:
        cmd.append("--force-dark-mode")
    cmd.append(target)
    # 출력 파이프를 붙잡고 멈추는 일을 막기 위해 출력은 버린다
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)

if not out.exists():
    sys.exit("스크린샷 실패")
if narrow:
    try:
        from PIL import Image
        with Image.open(out) as im:
            im.crop((0, 0, min(a.width, im.width), im.height)).save(out)
    except ImportError:
        print(f"(Pillow가 없어 자르지 못함: 왼쪽 {a.width}px만 보면 됨)")
print(f"saved {out}")
