"""
PDF 피드백 문서에서 'before 근거(원문 캡처)' 이미지를 자동 생성합니다.

- 방식: 키워드가 포함된 텍스트 영역을 찾아 주변만 잘라서 PNG로 저장
- 출력: UIUX_renewal(Portfolio)/screenshots/before/pdf/*.png

실행:
  python "UIUX_renewal(Portfolio)\\extract_pdf_snips.py"
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass(frozen=True)
class SnipSpec:
    out_name: str
    keywords: tuple[str, ...]


def _union_rect(rects: list[fitz.Rect]) -> fitz.Rect:
    r = rects[0]
    for rr in rects[1:]:
        r |= rr
    return r


def _expand_and_clamp(rect: fitz.Rect, page_rect: fitz.Rect, pad: float) -> fitz.Rect:
    r = fitz.Rect(rect)
    r.x0 -= pad
    r.y0 -= pad
    r.x1 += pad
    r.y1 += pad
    r.x0 = max(page_rect.x0, r.x0)
    r.y0 = max(page_rect.y0, r.y0)
    r.x1 = min(page_rect.x1, r.x1)
    r.y1 = min(page_rect.y1, r.y1)
    return r


def _find_clip_rect(doc: fitz.Document, keywords: tuple[str, ...]) -> tuple[int, fitz.Rect] | None:
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        rects: list[fitz.Rect] = []
        for kw in keywords:
            rects.extend(page.search_for(kw))
        if rects:
            union = _union_rect(rects)
            clip = _expand_and_clamp(union, page.rect, pad=36)
            return page_index, clip
    return None


def _render_clip(page: fitz.Page, clip: fitz.Rect, zoom: float = 2.0) -> fitz.Pixmap:
    mat = fitz.Matrix(zoom, zoom)
    return page.get_pixmap(matrix=mat, clip=clip, alpha=False)


def main() -> int:
    # 콘솔 환경에 따라 한글 출력이 깨지는 문제 방어
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    base_dir = Path(__file__).resolve().parent
    pdf_candidates = list(base_dir.glob("*.pdf"))
    if not pdf_candidates:
        print(f"[ERR] No PDF found in: {base_dir}", file=sys.stderr)
        return 2

    # 폴더에 PDF가 1개라고 가정(현재 구조). 여러 개면 첫 번째 사용.
    pdf_path = pdf_candidates[0]
    out_dir = base_dir / "screenshots" / "before" / "pdf"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Using PDF: {pdf_path.name}")

    specs: list[SnipSpec] = [
        SnipSpec("pdf-mainpage-impact.png", ("임팩트", "테트리스", "브랜드")),
        SnipSpec("pdf-stack-buttons.png", ("버튼 UI", "액션이 없")),
        SnipSpec("pdf-bottom-fixed.png", ("하단 고정", "상시 고정")),
        SnipSpec("pdf-filters-hover.png", ("검색 필터", "호버", "노션")),
        SnipSpec("pdf-detail-sidebar.png", ("왼쪽", "고정 메뉴", "잘려")),
        SnipSpec("pdf-ai-assistant.png", ("AI", "비서", "컨셉")),
        # 프로젝트 히스토리/AI 메시지 흐름 관련 피드백 근거
        SnipSpec("pdf-project-history.png", ("프로젝트 히스토리", "히스토리", "AI 메시지")),
    ]

    doc = fitz.open(pdf_path)
    written = 0
    for spec in specs:
        found = _find_clip_rect(doc, spec.keywords)
        if not found:
            print(f"[WARN] No matches for {spec.out_name}: {spec.keywords}")
            continue

        page_index, clip = found
        page = doc.load_page(page_index)
        pix = _render_clip(page, clip, zoom=2.0)
        out_path = out_dir / spec.out_name
        pix.save(out_path.as_posix())
        print(f"[OK] {spec.out_name} (page {page_index + 1}) -> {out_path}")
        written += 1

    print(f"Done. Written {written} file(s) into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

