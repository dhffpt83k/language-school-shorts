"""
Language School · 대화 엑셀 → 쇼츠 게임용 JSON 변환기

사용법:
    python xlsx_to_json.py Language_School_All_Dialogues.xlsx
    python xlsx_to_json.py 입력.xlsx -o Assets/Resources/dialogues.json

엑셀만 고치고 이 스크립트를 다시 돌리면 게임 데이터가 갱신됩니다.
Claude(토큰) 없이 동작합니다. 필요한 패키지: openpyxl
"""
import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path

import openpyxl

SHEET = "장면 대화"
COLS = ["chapter", "week", "scene", "part", "id", "level", "line",
        "speaker", "role", "en", "ko", "feedback"]

ROLE_LISTEN = "듣기"
ROLE_CORRECT = "정답 (말하기)"
ROLE_WRONG = "오답 선택지"
ROLE_CHOICE = "이야기 선택"
ROLE_CLOSING = "마무리"
KNOWN_ROLES = {ROLE_LISTEN, ROLE_CORRECT, ROLE_WRONG, ROLE_CHOICE, ROLE_CLOSING}


def clean(v):
    return "" if v is None else str(v).strip()


def read_rows(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        sys.exit(f"'{SHEET}' 시트를 찾을 수 없어요. 시트 목록: {wb.sheetnames}")
    rows = []
    for i, r in enumerate(wb[SHEET].iter_rows(values_only=True)):
        if i == 0 or all(v is None for v in r):
            continue
        d = dict(zip(COLS, r))
        d["_row"] = i + 1  # 엑셀 행 번호 (오류 위치 표시용)
        rows.append(d)
    return rows


def condition_of(part):
    m = re.search(r"\((c\d+=\w+)\)", part)
    return m.group(1) if m else ""


def build_cards(rows, problems):
    groups = OrderedDict()
    for r in rows:
        key = (r["chapter"], clean(r["scene"]), clean(r["id"]), clean(r["part"]), r["level"])
        groups.setdefault(key, []).append(r)

    # 같은 대화 ID가 서로 다른 장면에 쓰였는지 확인 (쓰였으면 key에 장 번호를 붙여 구분)
    scenes_per_id = {}
    for (ch, scene, did, part, level) in groups:
        scenes_per_id.setdefault(did, set()).add((ch, scene))
    for did, sc in scenes_per_id.items():
        if len(sc) > 1:
            names = ", ".join(f"{c}장 '{n}'" for c, n in sorted(sc))
            problems.append((None, f"[주의] 대화 ID '{did}'가 여러 장면에 쓰임: {names} — 장 번호를 붙여 따로 처리했어요"))

    cards = []
    for (ch, scene, did, part, level), items in groups.items():
        items.sort(key=lambda x: x["line"] or 0)
        first = items[0]
        cond = condition_of(part)
        card = {
            "key": f"{did}{'_ch' + str(ch) if len(scenes_per_id[did]) > 1 else ''}{'@' + cond if cond else ''}_L{level}",
            "id": did,
            "chapter": first["chapter"] or 0,
            "week": clean(first["week"]),
            "scene": clean(first["scene"]),
            "part": part,
            "condition": cond,
            # 조건부(분기) 장면은 스토리 모드 전용, 쇼츠 랜덤 풀에서는 기본 제외
            "inShortsPool": cond == "",
            "level": int(level),
            "steps": [],
        }
        step = None
        for r in items:
            role = clean(r["role"])
            if role not in KNOWN_ROLES:
                problems.append((r["_row"], f"알 수 없는 역할 '{role}'"))
                continue
            if role in (ROLE_LISTEN, ROLE_CLOSING):
                step = {
                    "speaker": clean(r["speaker"]),
                    "en": clean(r["en"]),
                    "ko": clean(r["ko"]),
                    "isClosing": role == ROLE_CLOSING,
                    "isStoryChoice": False,
                    "options": [],
                    "_row": r["_row"],
                }
                card["steps"].append(step)
                continue
            if step is None or step["isClosing"]:
                problems.append((r["_row"], "앞에 상대 대사(듣기) 없이 내 대사가 나옴"))
                continue
            fb = clean(r["feedback"])
            opt = {
                "en": clean(r["en"]),
                "ko": clean(r["ko"]),
                "correct": role in (ROLE_CORRECT, ROLE_CHOICE),
                "feedback": "" if role == ROLE_CHOICE else fb,
                "setFlag": "",
            }
            if role == ROLE_CHOICE:
                step["isStoryChoice"] = True
                m = re.search(r"(c\d+=\w+)", fb)
                opt["setFlag"] = m.group(1) if m else ""
            step["options"].append(opt)
        # 풀어야 할 문제(오답이 있는 질문이나 이야기 선택)가 하나도 없으면 쇼츠 풀에서 제외
        card["hasQuiz"] = any(
            s["isStoryChoice"] or any(not o["correct"] for o in s["options"])
            for s in card["steps"])
        card["inShortsPool"] = card["inShortsPool"] and card["hasQuiz"]
        cards.append(card)
    return cards


def validate(cards, problems):
    by_id_levels = {}
    for c in cards:
        where = f"{c['key']} ({c['scene']})"
        by_id_levels.setdefault((c["key"].rsplit("_L", 1)[0]), set()).add(c["level"])
        if not c["steps"]:
            problems.append((None, f"{where}: 대사가 하나도 없음"))
        if c["steps"] and not c["steps"][-1]["isClosing"]:
            problems.append((c["steps"][-1]["_row"], f"{where}: 마무리 대사가 없음"))
        for s in c["steps"]:
            row = s["_row"]
            if not s["en"]:
                problems.append((row, f"{where}: 상대 대사 영어가 비어 있음"))
            if not s["ko"]:
                problems.append((row, f"{where}: 상대 대사 번역이 비어 있음"))
            if s["isClosing"]:
                continue
            opts = s["options"]
            n_correct = sum(o["correct"] for o in opts)
            if not opts:
                problems.append((row, f"{where}: '{s['en'][:30]}' 뒤에 내 대사(선택지)가 없음"))
                continue
            if s["isStoryChoice"]:
                if len(opts) < 2:
                    problems.append((row, f"{where}: 이야기 선택지가 1개뿐"))
                if any(not o["setFlag"] for o in opts):
                    problems.append((row, f"{where}: 이야기 선택에 'c숫자=값' 표시가 없음"))
            else:
                if n_correct != 1:
                    problems.append((row, f"{where}: 정답이 {n_correct}개 (1개여야 함)"))
                if len(opts) - n_correct < 1 and c["hasQuiz"]:
                    problems.append((row, f"{where}: 오답 선택지가 없음"))
                for o in opts:
                    if not o["correct"] and not o["feedback"]:
                        problems.append((row, f"{where}: 오답 '{o['en'][:30]}'에 피드백이 없음"))
            texts = [o["en"].lower() for o in opts]
            for t, k in Counter(texts).items():
                if k > 1:
                    problems.append((row, f"{where}: 같은 선택지가 {k}번 나옴 — '{t[:30]}'"))
            for o in opts:
                if not o["en"] or not o["ko"]:
                    problems.append((row, f"{where}: 선택지 영어/번역이 비어 있음"))
    for base, lv in by_id_levels.items():
        missing = sorted({1, 2, 3, 4, 5} - lv)
        if missing:
            problems.append((None, f"{base}: 레벨 {missing} 없음"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("-o", "--out", default="dialogues.json")
    ap.add_argument("--report", default="validation_report.txt")
    args = ap.parse_args()

    problems = []
    rows = read_rows(args.xlsx)
    cards = build_cards(rows, problems)
    validate(cards, problems)

    for c in cards:  # 내부용 필드 제거
        for s in c["steps"]:
            s.pop("_row", None)

    pool = [c for c in cards if c["inShortsPool"]]
    no_quiz = sorted({c["scene"] for c in cards if not c["hasQuiz"]})
    data = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": Path(args.xlsx).name,
        "cardCount": len(cards),
        "shortsPoolCount": len(pool),
        "cards": cards,
    }
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        f"변환 결과: {len(rows)}줄 → 카드 {len(cards)}장 (쇼츠 풀 {len(pool)}장 / 제외 {len(cards) - len(pool)}장: "
        f"조건부 {sum(1 for c in cards if c['condition'])}장, 풀 문제 없음 {sum(1 for c in cards if not c['hasQuiz'])}장)",
        f"장면 {len({(c['chapter'], c['scene']) for c in cards})}개 × 레벨 1~5",
        f"풀 문제가 없어 쇼츠에서 뺀 장면: {', '.join(no_quiz) or '없음'}",
        "",
        f"검사 결과: 문제 {len(problems)}건",
    ]
    for row, msg in problems:
        lines.append(f"  - {'엑셀 ' + str(row) + '행: ' if row else ''}{msg}")
    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:5]))
    print(f"→ {args.out}, {args.report}")


if __name__ == "__main__":
    main()
