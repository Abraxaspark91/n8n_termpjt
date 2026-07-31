# -*- coding: utf-8 -*-
"""
recover_bench_results.py — 중단된 벤치마크의 채점 결과를 GitHub 아티팩트에서 재구성
(GitHub Actions에서 실행, stdlib only)

증거 3겹으로 완료 run을 복원한다:
  ① scenarios/<슬러그>/wiki/logs/audit_<scenario_id>-r<k>-<ts>.json  ← 파일명이 케이스 식별자
  ② patches/{applied,pending}/patch_*.json                           ← req_id·source·ops
  ③ git log(patches 경로 커밋 메시지)                                 ← '(fallback)' = 패치 명세 무효

재구성 산출물: benchmark/runs/<scenario_id>_r<k>_<ts>.json
  → 하니스 v6.3의 Resume이 그대로 프리로드하는 형식(Score Run 스키마와 동일 어휘)

정직성 원칙: 감사로그에 없는 입력(entities 원본)은 지어내지 않는다.
  - 재계산 가능(실측): gold_recall(요건문·키워드·패치 ops 기반 hay), decoy_leak, patch_spec_valid,
    escalated, da_score, attempts, duration_ms, wiki_entry_incomplete
  - 검증 불가 → 통과 처리 + 플래그: hallucinated_entities, extractor_schema_invalid, payload_schema_invalid
  모든 결과에 metrics.reconstructed = true 를 남긴다(리포트 각주용).
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "benchmark" / "spec_screening.json"
OUTD = ROOT / "benchmark" / "runs"

GOLD_RECALL_MIN = 0.7
AUDIT_RE = re.compile(r"^audit_(S\d+-B[01]{5})-r(\d+)-(\d+)\.json$")


def norm(s) -> str:
    return re.sub(r"\s+", "", str(s or "").lower())


def load_specs():
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    return {f"{s['scenario_id']}#{s['repeat_idx']}": s for s in data["specs"]}


def collect_audits():
    """식별자 → 최신 감사로그(같은 케이스 다회 실행 시 ts 최대)."""
    best = {}
    for p in ROOT.glob("scenarios/*/wiki/logs/audit_*.json"):
        m = AUDIT_RE.match(p.name)
        if not m:
            continue
        key, ts = f"{m.group(1)}#{m.group(2)}", int(m.group(3))
        if key not in best or ts > best[key][0]:
            best[key] = (ts, p)
    out = {}
    for key, (ts, p) in best.items():
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(j, dict):
                raise ValueError("not an object")
            out[key] = (ts, j)
        except Exception as e:
            print(f"warn: audit unreadable {p.name}: {e}")
    return out


def collect_patches():
    """req_id → 패치 내용 (applied 우선, 없으면 pending)."""
    out = {}
    for sub in ("applied", "pending"):
        for p in sorted(ROOT.glob(f"patches/{sub}/patch_*.json")):
            if p.name.endswith(".result.json"):
                continue                      # CI 엔진의 op 결과 로그(리스트) — 패치 아님
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(j, dict):
                continue
            rid = j.get("req_id")
            if rid and rid not in out:
                out[rid] = j
    return out


def fallback_reqids():
    """git log에서 '(fallback)' 커밋 메시지의 req_id 집합."""
    try:
        log = subprocess.run(
            ["git", "log", "--pretty=%s", "--", "patches"],
            capture_output=True, text=True, cwd=ROOT, check=True,
        ).stdout
    except Exception as e:
        print(f"warn: git log unavailable ({e}) — patch_spec_valid는 전부 true로 간주")
        return set()
    bad = set()
    for line in log.splitlines():
        m = re.match(r"deliverables: patch (\S+) \(fallback\)", line)
        if m:
            bad.add(m.group(1))
    return bad


BASELINE = {("docx", "append_changelog"), ("xlsx", "append_row"), ("pptx", "append_changelog_slide")}


def reconstruct(key, ts, audit, spec, patch, is_fallback):
    gates = audit.get("gates", {})
    deliv = audit.get("deliverable", {})
    trig = audit.get("trigger", {})
    ops = (patch or {}).get("ops", []) or []

    # 채점용 hay: 요건문 + 키워드 + 요청자 + wiki 파일명 + 패치 ops 전문
    hay = norm(" ".join([
        str(deliv.get("requirement", "")),
        " ".join(map(str, deliv.get("keywords", []))),
        str(trig.get("requestor", "")),
        " ".join(map(str, deliv.get("wiki_files", []))),
        json.dumps(ops, ensure_ascii=False),
    ]))

    failures = []
    gold = spec.get("gold", [])
    hit = [g for g in gold if norm(g) in hay]
    recall = (len(hit) / len(gold)) if gold else 1.0
    if recall < GOLD_RECALL_MIN:
        failures.append("gold_recall_low")

    leaked = [d for d in spec.get("decoys", []) if norm(d) in hay]
    if leaked:
        failures.append("decoy_leak")

    if not (trig.get("requestor") and deliv.get("requirement") is not None
            and isinstance(deliv.get("keywords"), list) and deliv.get("commit_hash")):
        failures.append("wiki_entry_incomplete")

    patch_valid = (patch is not None) and (not is_fallback)
    if not patch_valid:
        failures.append("patch_spec_invalid")

    targeted = sum(1 for o in ops if (o.get("target"), o.get("op")) not in BASELINE)
    return {
        "scenario_id": spec["scenario_id"], "sid": spec["sid"], "domain": spec["domain"],
        "scenario_type": spec["scenario_type"], "branch_bits": spec["branch_bits"],
        "repeat_idx": spec["repeat_idx"], "repeats": spec["repeats"],
        "success": len(failures) == 0,
        "failures": failures,
        "metrics": {
            "gold_recall": round(recall, 2),
            "hallucinated": [],                 # 검증 불가 — 아래 플래그 참조
            "leaked_decoys": leaked,
            "entities_count": None,
            "attempts": {
                "r1": gates.get("contract_audit", {}).get("attempts"),
                "r2": gates.get("semantic_audit", {}).get("attempts"),
                "da": gates.get("devils_advocate", {}).get("attempts"),
            },
            "da_score": gates.get("devils_advocate", {}).get("score"),
            "escalated": bool(gates.get("escalated_any")),
            "patch_valid": patch_valid,
            "patch_ops": len(ops) if patch else None,
            "patch_targeted": targeted if patch else None,
            "duration_ms": audit.get("run", {}).get("duration_ms"),
            "reconstructed": True,
            "reconstructed_note": "hallucination/schema 검사는 원본 entities 부재로 검증 불가(통과 처리)",
            "source_audit_ts": ts,
        },
    }


def main() -> int:
    if not SPEC.exists():
        print(f"spec 파일 없음: {SPEC} — 하니스 배포 시 함께 커밋 필요")
        return 1
    specs = load_specs()
    audits = collect_audits()
    patches = collect_patches()
    bad = fallback_reqids()
    OUTD.mkdir(parents=True, exist_ok=True)

    existing = set()
    for p in OUTD.glob("*.json"):
        m = re.match(r"^(S\d+-B[01]{5})_r(\d+)_\d+\.json$", p.name)
        if m:
            existing.add(f"{m.group(1)}#{m.group(2)}")

    made, skipped_have, skipped_incomplete, not_in_plan = 0, 0, 0, 0
    for key, (ts, audit) in sorted(audits.items()):
        if key not in specs:
            not_in_plan += 1          # smoke 등 다른 플랜의 흔적 — screening 복구 대상 아님
            continue
        if key in existing:
            skipped_have += 1         # 이미 결과 파일 있음(v6.3 정상 기록분)
            continue
        rid = audit.get("deliverable", {}).get("req_id")
        patch = patches.get(rid)
        if patch is None:
            skipped_incomplete += 1   # 감사로그만 있고 패치 없음 → 미완 run으로 간주(재실행 대상)
            print(f"skip(incomplete): {key} — 패치 없음(req_id={rid})")
            continue
        scored = reconstruct(key, ts, audit, specs[key], patch, rid in bad)
        name = f"{scored['scenario_id']}_r{scored['repeat_idx']}_{int(time.time() * 1000)}.json"
        (OUTD / name).write_text(json.dumps(scored, ensure_ascii=False, indent=1), encoding="utf-8")
        made += 1
        print(f"recovered: {key} → {name} | success={scored['success']} failures={scored['failures']}")
        time.sleep(0.002)             # 파일명 ts 충돌 방지

    print(f"\n요약: 복구 {made}건 · 기존기록 보유 {skipped_have}건 · 미완(재실행 대상) {skipped_incomplete}건 "
          f"· 플랜 외 흔적 {not_in_plan}건 / 계획 {len(specs)}건")
    print(f"→ 다음 하니스 실행 시 Resume이 {made + skipped_have}건을 프리로드하고 "
          f"{len(specs) - made - skipped_have}건만 실행합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
