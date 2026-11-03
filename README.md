# pdf2html

강의자료 PDF를 챕터별 **한국어 설명 HTML 한 파일**로 만드는 Claude Code 스킬입니다.

- 모든 페이지를 빠짐없이 쉽게 설명합니다. 정의, 예시, 표, 코드, 수식, 그림, 문제까지 다룹니다.
- PDF 내용과 Claude가 덧붙인 내용을 색 박스로 구분합니다. 보충 설명은 보라, 슬라이드 오류 의심은 빨강입니다.
- `01A`, `01B`처럼 같은 장 번호에 알파벳이 붙은 PDF는 Part A/B로 묶어 HTML 하나에 넣습니다.
- 목차, 원본 슬라이드 임베드, 원본 페이지 대응표, 다크 모드가 들어간 오프라인 단일 파일입니다.
- `--everytime` 옵션을 붙이면 같은 폴더의 에브리타임 기출 캡처와 매핑 md를 찾아 관련 부분에 `📌 에타 Qn` 표시를 답니다.

페이지마다 한 섹션씩 쓰는 md 노트가 필요하면 [pdf2md](https://github.com/RainDrop3-skills/pdf2md)를 쓰세요.

## 설치

Claude Code 개인 스킬 폴더에 넣습니다.

```bash
# macOS / Linux / Git Bash
git clone https://github.com/RainDrop3-skills/pdf2html.git ~/.claude/skills/pdf2html
```

```powershell
# Windows PowerShell
git clone https://github.com/RainDrop3-skills/pdf2html.git "$env:USERPROFILE\.claude\skills\pdf2html"
```

필요한 것
- Python 3 (외부 패키지 설치 없음)
- poppler (`pdfinfo`, `pdftotext`, `pdftoppm`). Windows는 `winget install oschwartz10612.Poppler`
- 렌더링 확인용 Edge 또는 Chrome

## 사용

PDF가 있는 폴더에서 Claude Code에 이렇게 말하면 됩니다.

- "3장 관계대수 PDF를 설명 html로 만들어줘"
- "01~06 자료 html로 정리해줘"
- "아직 설명 html 없는 챕터 전부 만들어줘"
- "5장 html 만들어줘 --everytime"

결과는 PDF와 같은 폴더에 `NN. <챕터 제목> - 설명.html`로 저장됩니다.

## 구조

| 경로 | 내용 |
|---|---|
| `SKILL.md` | 작업 절차 (Claude가 읽는 지침) |
| `assets/template.html` | 공통 디자인 (CSS 토큰, 다크 모드, 목차, 박스, 대응표) |
| `scripts/extract_pages.py` | PDF → 페이지별 텍스트·이미지·요약 |
| `scripts/embed_pages.py` | 원본 슬라이드를 base64 PNG로 임베드 |
| `scripts/check.py` | 결과 검수 (대응표 커버리지, 링크, 태그, 자리표시자) |
| `scripts/html_text.py` | HTML에서 보이는 글자만 추출 |
| `scripts/screenshot.py` | 헤드리스 Edge/Chrome으로 렌더링해 PNG 저장 |
| `references/everytime.md` | `--everytime` 옵션 규칙 |

## 한계

- 학습 보조 자료입니다. 시험 기준은 원본 슬라이드 문구입니다.
- 판독이 어려운 그림이나 글씨는 추측하지 않고 원본 슬라이드를 함께 보여 줍니다.
