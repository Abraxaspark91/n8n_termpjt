# -*- coding: utf-8 -*-
"""
apply_deliverable_patch.py — W3 산출물 동기화 엔진 v2 (GitHub Actions에서 실행)

역할 분리(하이브리드):
  * 판단(무엇을 어떻게 고칠지)  = n8n 안의 Deliverable Patch Agent(LLM + 상태읽기 툴)
  * 조립(zip/OOXML 기계적 반영) = 이 스크립트 (지능 0, 조립 100)

입력: deliverables/patches/pending/patch_*.json
  - deliverable_patch/v2 : ops[] 기반 타깃 편집 (아래 OPS 어휘)
  - deliverable_patch/v1 : 구버전 append-only — 하위호환 유지(regression 방지)

v2 ops 어휘 (n8n 'Parse Patch Spec' 검증기와 1:1 동일해야 함):
  docx.append_changelog      {title?, bullets[], risks[], open_questions[], wiki_commit_url?}
  docx.append_after_heading  {heading, text, style?('List Bullet'|null)}
  docx.replace_paragraph     {match, new_text}          # match=기존 문단 '전체 텍스트' 정확일치
  xlsx.append_row            {sheet?='RTM', values[]}
  xlsx.update_by_req_id      {req_id, column, value}    # RTM에서 req_id 행 탐색, column=헤더명
  xlsx.update_cell           {sheet?='RTM', cell, value} # 예: cell='F3'
  pptx.append_changelog_slide{title, bullets[]}
  pptx.replace_text          {match, new_text}          # 전 슬라이드 문단 전체 텍스트 정확일치

안전 규칙: 삭제 없음 / 미일치 match·미지 op는 skip 후 로그 / 파일 없으면 부트스트랩 생성(멱등).
적용 후 상태 추출본을 deliverables/state/ 에 내보낸다(n8n 에이전트가 읽는 원천):
  산출물_설계서.md · 요구사항_추적표.csv · 보고_장표.md
결과 로그: applied/patch_<name>.result.json
"""
import csv
import io
import json
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from pptx.util import Inches, Pt as PPt

ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "deliverables"
PENDING = DELIV / "patches" / "pending"
APPLIED = DELIV / "patches" / "applied"
STATE = DELIV / "state"

DOCX = DELIV / "산출물_설계서.docx"
XLSX = DELIV / "요구사항_추적표.xlsx"
PPTX = DELIV / "보고_장표.pptx"

RTM_HEADER = ["req_id", "일시", "요청자", "소스", "결정", "요약",
              "영향 산출물", "변경유형", "DA점수", "위키 커밋"]
MAX_OPS = 12


# ── 부트스트랩 ────────────────────────────────────────────────────────
def ensure_docx() -> Document:
    if DOCX.exists():
        return Document(str(DOCX))
    doc = Document()
    doc.add_heading("산출물 설계서", level=0)
    doc.add_paragraph("W3 Agentic Organization 파이프라인이 관리하는 설계 문서입니다. "
                      "승인된 요건은 '변경 이력' 절과 본문 타깃 편집으로 자동 반영됩니다.")
    doc.add_heading("변경 이력", level=1)
    return doc


def ensure_xlsx():
    if XLSX.exists():
        wb = load_workbook(str(XLSX))
    else:
        wb = Workbook()
        wb.active.title = "RTM"
    if "RTM" not in wb.sheetnames:
        wb.create_sheet("RTM")
    ws = wb["RTM"]
    if ws.max_row == 1 and all(c.value is None for c in ws[1]):
        for col, h in enumerate(RTM_HEADER, start=1):
            ws.cell(row=1, column=col, value=h)
    return wb, ws


def ensure_pptx() -> Presentation:
    if PPTX.exists():
        return Presentation(str(PPTX))
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "W3 프로젝트 보고 장표"
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = "변경사항이 파이프라인에 의해 자동 반영됩니다."
    return prs


# ── docx ops ─────────────────────────────────────────────────────────
def docx_append_changelog(doc, p, op):
    doc.add_heading(op.get("title") or f"[{p.get('req_id', '-')}] {p.get('summary', '')[:60]}", level=2)
    meta = doc.add_paragraph()
    run = meta.add_run(f"일시 {p.get('ts', '-')} · 요청자 {p.get('requestor', '-')} · "
                       f"소스 {p.get('source', '-')} · 결정 {p.get('decision', '-')} · DA {p.get('da_score', '-')}")
    run.font.size = Pt(9)
    for b in op.get("bullets") or []:
        doc.add_paragraph(str(b), style="List Bullet")
    if op.get("risks"):
        doc.add_paragraph("리스크:", style="Intense Quote")
        for r in op["risks"]:
            doc.add_paragraph(str(r), style="List Bullet")
    if op.get("open_questions"):
        doc.add_paragraph("미해결 질문:", style="Intense Quote")
        for q in op["open_questions"]:
            doc.add_paragraph(str(q), style="List Bullet")
    if op.get("wiki_commit_url"):
        doc.add_paragraph(f"위키 커밋: {op['wiki_commit_url']}")
    return "applied"


def docx_append_after_heading(doc, p, op):
    target = str(op.get("heading", "")).strip()
    for para in doc.paragraphs:
        if para.style.name.lower().startswith("heading") and para.text.strip() == target:
            style = op.get("style") if op.get("style") in ("List Bullet", "Intense Quote") else None
            new = doc.add_paragraph(str(op.get("text", "")), style=style)
            para._p.addnext(new._p)          # heading 바로 뒤로 이동
            return "applied"
    return f"skipped: heading not found ({target})"


def docx_replace_paragraph(doc, p, op):
    match = str(op.get("match", ""))
    for para in doc.paragraphs:
        if para.text == match:
            for r in list(para.runs):
                r.text = ""
            (para.runs[0] if para.runs else para.add_run()).text = str(op.get("new_text", ""))
            return "applied"
    return "skipped: paragraph not found"


# ── xlsx ops ─────────────────────────────────────────────────────────
def xlsx_append_row(wb, p, op):
    ws = wb[op.get("sheet") or "RTM"] if (op.get("sheet") or "RTM") in wb.sheetnames else wb["RTM"]
    ws.append([("" if v is None else v) for v in (op.get("values") or [])])
    return "applied"


def xlsx_update_by_req_id(wb, p, op):
    ws = wb["RTM"]
    headers = [str(c.value or "") for c in ws[1]]
    col_name = str(op.get("column", ""))
    if col_name not in headers:
        return f"skipped: column not found ({col_name})"
    col = headers.index(col_name) + 1
    for r in range(2, ws.max_row + 1):
        if str(ws.cell(row=r, column=1).value or "") == str(op.get("req_id", "")):
            ws.cell(row=r, column=col, value=op.get("value"))
            return "applied"
    return f"skipped: req_id row not found ({op.get('req_id')})"


def xlsx_update_cell(wb, p, op):
    sheet = op.get("sheet") or "RTM"
    if sheet not in wb.sheetnames:
        return f"skipped: sheet not found ({sheet})"
    try:
        wb[sheet][str(op.get("cell"))] = op.get("value")
        return "applied"
    except Exception as e:
        return f"skipped: bad cell ({e})"


# ── pptx ops ─────────────────────────────────────────────────────────
def pptx_append_changelog_slide(prs, p, op):
    layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = str(op.get("title") or f"변경사항 — {p.get('req_id', '-')}")
    body = None
    for ph in slide.placeholders:
        if ph != slide.shapes.title and ph.has_text_frame:
            body = ph.text_frame
            break
    if body is None:
        body = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(9), Inches(5)).text_frame
    bullets = [str(b) for b in (op.get("bullets") or ["(내용 없음)"])]
    body.text = bullets[0]
    for ln in bullets[1:]:
        para = body.add_paragraph()
        para.text = ln
        para.font.size = PPt(14)
    return "applied"


def pptx_replace_text(prs, p, op):
    match = str(op.get("match", ""))
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                if "".join(r.text for r in para.runs) == match or para.text == match:
                    for r in list(para.runs):
                        r.text = ""
                    (para.runs[0] if para.runs else para.add_run()).text = str(op.get("new_text", ""))
                    return "applied"
    return "skipped: text not found"


OPS = {
    ("docx", "append_changelog"): ("doc", docx_append_changelog),
    ("docx", "append_after_heading"): ("doc", docx_append_after_heading),
    ("docx", "replace_paragraph"): ("doc", docx_replace_paragraph),
    ("xlsx", "append_row"): ("wb", xlsx_append_row),
    ("xlsx", "update_by_req_id"): ("wb", xlsx_update_by_req_id),
    ("xlsx", "update_cell"): ("wb", xlsx_update_cell),
    ("pptx", "append_changelog_slide"): ("prs", pptx_append_changelog_slide),
    ("pptx", "replace_text"): ("prs", pptx_replace_text),
}


def v1_to_ops(p):
    """v1 패치(하위호환)를 baseline 3-ops로 변환."""
    ads = p.get("affected_deliverables") or [{}]
    return [
        {"target": "docx", "op": "append_changelog",
         "bullets": p.get("changes", []), "risks": p.get("risks", []),
         "open_questions": p.get("open_questions", []), "wiki_commit_url": p.get("wiki_commit_url", "")},
        {"target": "xlsx", "op": "append_row", "sheet": "RTM", "values": [
            p.get("req_id", "-"), p.get("ts", "-"), p.get("requestor", "-"), p.get("source", "-"),
            p.get("decision", "-"), (p.get("summary", "") or "")[:200],
            "; ".join(str(a.get("name", "-")) for a in ads),
            "; ".join(str(a.get("change_type", "-")) for a in ads),
            p.get("da_score", ""), p.get("wiki_commit_url", "")]},
        {"target": "pptx", "op": "append_changelog_slide",
         "title": f"변경사항 — {p.get('req_id', '-')}",
         "bullets": [f"요청자: {p.get('requestor', '-')} · 결정: {p.get('decision', '-')}"]
                    + [f"• {c}" for c in (p.get("changes") or [])[:6]]},
    ]


# ── 상태 추출본 (n8n 에이전트가 읽는 원천) ────────────────────────────
def export_state(doc, wb, prs):
    STATE.mkdir(parents=True, exist_ok=True)
    lines = []
    for para in doc.paragraphs:
        st, tx = para.style.name, para.text
        if not tx.strip():
            continue
        if st == "Title":
            lines.append(f"# {tx}")
        elif st.lower().startswith("heading"):
            try:
                lv = int(st.split()[-1])
            except Exception:
                lv = 1
            lines.append("#" * min(6, lv + 1) + f" {tx}")
        elif st == "List Bullet":
            lines.append(f"- {tx}")
        else:
            lines.append(tx)
    (STATE / "산출물_설계서.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    buf = io.StringIO()
    w = csv.writer(buf)
    for row in wb["RTM"].iter_rows(values_only=True):
        w.writerow(["" if v is None else v for v in row])
    (STATE / "요구사항_추적표.csv").write_text(buf.getvalue(), encoding="utf-8")

    out = []
    for i, slide in enumerate(prs.slides, start=1):
        title = slide.shapes.title.text if slide.shapes.title is not None else "(제목 없음)"
        out.append(f"## Slide {i}: {title}")
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape != slide.shapes.title:
                for para in shape.text_frame.paragraphs:
                    if para.text.strip():
                        out.append(f"- {para.text}")
    (STATE / "보고_장표.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    PENDING.mkdir(parents=True, exist_ok=True)
    APPLIED.mkdir(parents=True, exist_ok=True)
    patches = sorted(PENDING.glob("patch_*.json"))

    doc = ensure_docx()
    wb, ws = ensure_xlsx()
    prs = ensure_pptx()
    ctx = {"doc": doc, "wb": wb, "prs": prs}

    done = []
    for path in patches:
        try:
            p = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip (invalid json): {path.name}: {e}")
            continue
        schema = p.get("schema")
        if schema == "deliverable_patch/v2":
            ops = p.get("ops") or []
        elif schema == "deliverable_patch/v1":
            ops = v1_to_ops(p)
        else:
            print(f"skip (unknown schema): {path.name}")
            continue

        results = []
        for op in ops[:MAX_OPS]:
            key = (op.get("target"), op.get("op"))
            if key not in OPS:
                results.append({"op": op, "result": f"skipped: unknown op {key}"})
                continue
            kind, fn = OPS[key]
            try:
                results.append({"op": op, "result": fn(ctx[kind], p, op)})
            except Exception as e:
                results.append({"op": op, "result": f"skipped: error {e}"})
        done.append((path, results))
        print(f"processed {path.name}: "
              f"{sum(1 for r in results if r['result'] == 'applied')}/{len(results)} ops applied")

    if done:
        doc.save(str(DOCX))
        wb.save(str(XLSX))
        prs.save(str(PPTX))
    export_state(doc, wb, prs)          # 패치가 없어도 상태본은 최신화(멱등)
    for path, results in done:
        (APPLIED / (path.stem + ".result.json")).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.move(str(path), str(APPLIED / path.name))
    print(f"done: {len(done)} patch(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
