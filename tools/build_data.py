"""
엑셀 → 앱 데이터 (data/cards.json, data/extras.json, data/version.json)

    python tools/build_data.py                       # content/ 안의 엑셀 사용
    python tools/build_data.py 다른파일.xlsx

검사에서 문제가 나오면 실패(종료 코드 1)해서, GitHub에서 배포가 멈춰요.
그래서 엑셀에 실수가 있어도 앱에 깨진 데이터가 올라가지 않아요.
'[주의]'로 시작하는 항목은 경고일 뿐이라 배포를 막지 않아요.
"""
import hashlib
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_to_json import read_rows, build_cards, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))


def rows_of(wb, name):
    if name not in wb.sheetnames:
        return []
    out = []
    for i, r in enumerate(wb[name].iter_rows(values_only=True)):
        if i and any(v is not None for v in r):
            out.append(r)
    return out


def build_extras(path, problems):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    # 행인 대화 → 엿듣기 카드
    conv = OrderedDict()
    for place, no, sp, en, ko in [r[:5] for r in rows_of(wb, "행인 대화")]:
        conv.setdefault((place, no), {})[sp] = [en, ko]
    overhear = [{"p": p, "a": v["A"], "b": v["B"]} for (p, _), v in conv.items() if "A" in v and "B" in v]

    # 휴대폰 메시지 → 메시지 카드 (엄마 방은 한국어라 제외, 분기 조건 있는 메시지 제외)
    th = OrderedDict()
    for ch, wk, room, sender, kind, en, ko, cond in [r[:8] for r in rows_of(wb, "휴대폰 메시지")]:
        if room == "엄마" or cond:
            continue
        t = th.setdefault((ch, room), {"c": ch, "w": wk, "r": room, "m": [], "rep": []})
        if kind == "답장 선택지":
            t["rep"].append([en, ko])
        else:
            t["m"].append([sender, en, ko])
    phone = [t for t in th.values() if t["m"]]

    # 명절 퀴즈
    quiz = []
    for n, q, a, wrong, exp in [r[:5] for r in rows_of(wb, "명절 퀴즈")]:
        xs = [s.strip() for s in str(wrong or "").split(" / ") if s.strip()]
        if not q or not a or len(xs) < 2:
            problems.append((None, f"명절 퀴즈 {n}번: 질문/정답/오답(2개 이상)을 확인해 주세요"))
            continue
        quiz.append({"q": q, "a": a, "x": xs, "e": exp or ""})

    # 일기
    diary = {str(r[0]): [r[1], r[2], r[3]] for r in rows_of(wb, "일기") if r[0] is not None}
    return {"overhear": overhear, "phone": phone, "quiz": quiz, "diary": diary}


def compact_cards(cards):
    out = []
    for c in cards:
        if not c["inShortsPool"]:
            continue
        t = [[s["speaker"], s["en"], s["ko"],
              1 if s["isClosing"] else (2 if s["isStoryChoice"] else 0),
              [[o["en"], o["ko"], 1 if o["correct"] else 0, o["feedback"]] for o in s["options"]]]
             for s in c["steps"]]
        out.append({"k": c["key"], "c": c["chapter"], "s": c["scene"], "w": c["week"], "l": c["level"], "t": t})
    return out


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else next(iter(sorted((ROOT / "content").glob("*.xlsx"))), None)
    if not src or not src.exists():
        sys.exit("content/ 폴더에 엑셀 파일이 없어요.")

    problems = []
    cards = build_cards(read_rows(src), problems)
    validate(cards, problems)
    for c in cards:
        for s in c["steps"]:
            s.pop("_row", None)
    extras = build_extras(src, problems)
    pool = compact_cards(cards)

    DATA.mkdir(exist_ok=True)
    cards_txt = "[\n" + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in pool) + "\n]\n"
    extras_txt = json.dumps(extras, ensure_ascii=False, separators=(",", ":"))
    (DATA / "cards.json").write_text(cards_txt, encoding="utf-8")
    (DATA / "extras.json").write_text(extras_txt, encoding="utf-8")

    digest = hashlib.sha1((cards_txt + extras_txt).encode("utf-8")).hexdigest()[:10]
    version = {"version": digest, "builtAt": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
               "cards": len(pool), "scenes": len({c["k"].rsplit("_L", 1)[0] for c in pool})}
    (DATA / "version.json").write_text(json.dumps(version, ensure_ascii=False), encoding="utf-8")

    errors = [p for p in problems if not p[1].startswith("[주의]")]
    warns = [p for p in problems if p[1].startswith("[주의]")]
    print(f"카드 {len(pool)}장 · 엿듣기 {len(extras['overhear'])} · 메시지 {len(extras['phone'])} · "
          f"퀴즈 {len(extras['quiz'])} · 일기 {len(extras['diary'])} · 버전 {digest}")
    for row, msg in warns + errors:
        print(f"  {'엑셀 ' + str(row) + '행: ' if row else ''}{msg}")
    if errors:
        print(f"\n문제 {len(errors)}건 — 고친 뒤 다시 올려 주세요. (배포를 멈춥니다)")
        sys.exit(1)
    print("검사 통과")


if __name__ == "__main__":
    main()
