"""
쿠팡 최저가 추적기
  python tracker.py          : 가격 수집 + 웹페이지 생성 (API 키 필요)
  python tracker.py --demo   : 가짜 데이터로 웹페이지 미리보기 (API 키 불필요)
  python tracker.py --build  : 수집 없이 웹페이지만 다시 생성
"""
import json
import os
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config

ROOT = Path(__file__).parent
DATA = ROOT / "data"
HISTORY_FILE = DATA / "history.json"
STATE_FILE = DATA / "state.json"
TEMPLATE = ROOT / "template.html"
OUT = ROOT / "docs" / "index.html"
KST = timezone(timedelta(hours=9))
MAX_POINTS = 400


def now_kst():
    return datetime.now(KST)


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")


# ---------------------------------------------------------------- 수집
def record(history, item, source, ts, rank=None):
    pid = str(item.get("productId"))
    price = item.get("productPrice")
    if not pid or pid == "None" or not price:
        return
    price = int(price)
    p = history.setdefault(pid, {"points": [], "sources": []})
    p.update({
        "name": item.get("productName", p.get("name", "")),
        "image": item.get("productImage", p.get("image", "")),
        "url": item.get("productUrl", p.get("url", "")),
        "rocket": bool(item.get("isRocket", p.get("rocket", False))),
        "last_seen": ts,
    })
    if source not in p["sources"]:
        p["sources"].append(source)
    if rank is not None:
        p["rank"] = rank
    pts = p["points"]
    if pts and pts[-1][1] == price and pts[-1][0][:10] == ts[:10]:
        return  # 같은 날 같은 가격이면 기록 안 함 (용량 절약)
    if pts and pts[-1][0] == ts:
        pts[-1][1] = min(pts[-1][1], price)
    else:
        pts.append([ts, price])
    del pts[:-MAX_POINTS]


def collect(history):
    from coupang_api import CoupangAPI
    ak, sk = os.environ.get("COUPANG_ACCESS_KEY"), os.environ.get("COUPANG_SECRET_KEY")
    if not ak or not sk:
        sys.exit("COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 환경변수가 없습니다. README를 확인하세요.")
    api = CoupangAPI(ak, sk, config.SUB_ID or None)
    ts = now_kst().strftime("%Y-%m-%d %H:%M")
    count = 0

    if config.USE_GOLDBOX:
        try:
            for i, it in enumerate(api.goldbox()):
                record(history, it, "골드박스", ts); count += 1
        except Exception as e:
            print("골드박스 실패:", e)

    for cid, cname in config.BEST_CATEGORIES.items():
        try:
            for it in api.best(cid, config.BEST_PER_CATEGORY):
                record(history, it, cname, ts, rank=it.get("rank")); count += 1
        except Exception as e:
            print(f"베스트 {cname} 실패:", e)

    # 검색은 1시간 10회 제한 → 순서대로 돌아가며 몇 개씩만
    state = load(STATE_FILE, {"kw_index": 0})
    kws = config.KEYWORDS
    n = min(config.KEYWORDS_PER_RUN, 10, len(kws))
    for k in range(n):
        kw = kws[(state["kw_index"] + k) % len(kws)]
        try:
            for it in api.search(kw, config.RESULTS_PER_KEYWORD):
                record(history, it, f"검색:{kw}", ts); count += 1
        except Exception as e:
            print(f"검색 '{kw}' 실패, 이번 회차 검색 중단:", e)
            break  # 연속 실패 시 계정 정지 위험 → 바로 멈춤
    if kws:
        state["kw_index"] = (state["kw_index"] + n) % len(kws)
    save(STATE_FILE, state)
    print(f"{ts} 수집 완료: {count}건, 추적 중인 상품 {len(history)}개")


def prune(history):
    cutoff = (now_kst() - timedelta(days=config.KEEP_DAYS)).strftime("%Y-%m-%d")
    for pid in [k for k, v in history.items() if v.get("last_seen", "")[:10] < cutoff]:
        del history[pid]


# ---------------------------------------------------------------- 핫딜 판정
def analyze(history):
    out = []
    recent_cut = (now_kst() - timedelta(days=2)).strftime("%Y-%m-%d")
    for pid, p in history.items():
        pts = p["points"]
        if not pts:
            continue
        cur = pts[-1][1]
        prices = [x[1] for x in pts]
        prev = prices[:-1]
        typical = statistics.median(prev) if prev else cur
        drop = round((typical - cur) / typical * 100, 1) if typical else 0
        enough = len(pts) >= config.MIN_POINTS_FOR_DEAL
        is_low = enough and cur <= min(prev)
        hot = enough and drop >= config.HOT_DROP_PERCENT and p.get("last_seen", "") >= recent_cut
        out.append({
            "id": pid, "name": p.get("name", ""), "image": p.get("image", ""),
            "url": p.get("url", ""), "rocket": p.get("rocket", False),
            "sources": p.get("sources", []), "rank": p.get("rank"),
            "cur": cur, "min": min(prices), "max": max(prices), "typical": int(typical),
            "drop": drop, "low": is_low, "hot": hot,
            "active": p.get("last_seen", "") >= recent_cut,
            "points": pts,
        })
    out.sort(key=lambda x: (not x["hot"], not x["low"], -x["drop"], x["rank"] or 999))
    return out


# ---------------------------------------------------------------- 웹페이지
def build(history):
    items = analyze(history)
    # 페이지가 너무 무거워지지 않게: 핫딜/최저가 전부 + 나머지 상위 600개
    keep = [i for i in items if i["hot"] or i["low"]]
    keep += [i for i in items if not (i["hot"] or i["low"]) and i["active"]][:600]
    payload = {
        "title": config.SITE_TITLE,
        "updated": now_kst().strftime("%Y-%m-%d %H:%M"),
        "hotPercent": config.HOT_DROP_PERCENT,
        "total": len(history),
        "items": keep,
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    data_js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/null", data_js).replace("__TITLE__", config.SITE_TITLE)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    hot = sum(1 for i in keep if i["hot"])
    print(f"웹페이지 생성: {OUT} (핫딜 {hot}개, 표시 {len(keep)}개)")


# ---------------------------------------------------------------- 데모
def demo_history():
    random.seed(7)
    names = [("삼다수 2L x 12병", 9900), ("크리넥스 3겹 데코 30롤", 21900),
             ("다우니 세탁세제 3.2L", 18900), ("하기스 맥스드라이 4단계 168매", 52900),
             ("허닭 닭가슴살 100g x 30팩", 39800), ("맥심 모카골드 180T", 23900),
             ("려 자양윤모 샴푸 1L x 2", 21900), ("애플 에어팟 프로 2세대", 299000),
             ("코카콜라 제로 355ml x 24캔", 17900), ("곰곰 무항생제 계란 30구", 8990),
             ("탐사 물티슈 100매 x 10팩", 9980), ("로지텍 무선 마우스 M331", 22900),
             ("오뚜기 진라면 순한맛 40개", 25400), ("필립스 전동칫솔 3100", 59000),
             ("락앤락 밀폐용기 10종 세트", 24900), ("일리 캡슐커피 100개입", 69000)]
    hist = {}
    start = now_kst() - timedelta(days=30)
    for idx, (name, base) in enumerate(names):
        pts, price = [], base
        for d in range(31):
            if random.random() < 0.35 or d == 0:
                price = int(base * random.uniform(0.9, 1.08) / 10) * 10
                pts.append([(start + timedelta(days=d)).strftime("%Y-%m-%d 09:00"), price])
        if idx % 3 == 0:  # 일부 상품은 오늘 크게 떨어진 것으로
            pts.append([now_kst().strftime("%Y-%m-%d %H:%M"), int(base * 0.78 / 10) * 10])
        hist[str(10000 + idx)] = {
            "name": name, "image": "", "url": "https://link.coupang.com/",
            "rocket": idx % 2 == 0, "sources": ["데모"], "rank": idx + 1,
            "last_seen": now_kst().strftime("%Y-%m-%d %H:%M"), "points": pts}
    return hist


def main():
    args = sys.argv[1:]
    if "--demo" in args:
        build(demo_history()); return
    history = load(HISTORY_FILE, {})
    if "--build" not in args:
        collect(history)
        prune(history)
        save(HISTORY_FILE, history)
    build(history)


if __name__ == "__main__":
    main()
