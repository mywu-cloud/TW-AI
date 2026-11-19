#!/usr/bin/env python3
"""
台灣 AI 科技財報 — 資料更新

來源（依序合併）：
 1. mywu-cloud/fineps   data/eps-twse.json、eps-tpex.json、prices.json、stock-concepts.json
    （全市場季 EPS 含「搶先報」暫估、收盤價、概念股標籤；由該 repo 的 Actions 每日更新）
 2. mywu-cloud/finrev   data/revenue-twse.json、revenue-tpex.json（全市場月營收，近 2 年）
 3. FinMind（每檔每 FINMIND_DAYS 天一次）：2019 起月營收、季 EPS、現金股利 → 長期歷史與官方數字
    無 token 每小時約 300 次；有 secrets.FINMIND_TOKEN 會自動帶入。

輸出：public/data/tw-ai.json
用法：python scripts/fetch.py [--no-finmind] [--offline DIR]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "companies.json")
OUT = os.path.join(ROOT, "public", "data", "tw-ai.json")
RAW = "https://raw.githubusercontent.com/mywu-cloud/{}/main/data/{}"
FM = "https://api.finmindtrade.com/api/v4/data"
TOKEN = os.environ.get("FINMIND_TOKEN", "")
FINMIND_DAYS = float(os.environ.get("FINMIND_DAYS", "7"))
MAX_FINMIND = int(os.environ.get("MAX_FINMIND", "270"))
START = "2019-01-01"


def r2(v, n=2):
    return None if v is None else round(float(v), n)


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tw-ai-tracker"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:  # noqa
            if i == tries - 1:
                print(f"[warn] {url[:90]} → {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))


def load_src(offline, repo, fn):
    if offline:
        p = os.path.join(offline, repo, "data", fn)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return get_json(RAW.format(repo, fn))


# ---------- FinMind ----------
class FinMind:
    def __init__(self, budget):
        self.budget, self.calls, self.dead = budget, 0, False

    def get(self, dataset, code, start):
        if self.dead or self.calls >= self.budget:
            return None
        q = {"dataset": dataset, "data_id": code, "start_date": start}
        if TOKEN:
            q["token"] = TOKEN
        self.calls += 1
        j = get_json(FM + "?" + urllib.parse.urlencode(q))
        time.sleep(0.35)
        if not j:
            return None
        if j.get("status") != 200:
            print(f"[finmind] {dataset} {code}: {j.get('msg')}", file=sys.stderr)
            if j.get("status") in (402, 403) or "limit" in str(j.get("msg", "")).lower():
                self.dead = True  # 額度用完，本次停止
            return None
        return j.get("data", [])


def roc_year(s):
    m = re.match(r"(\d{2,3})年", s or "")
    return int(m.group(1)) + 1911 if m else None


def finmind_refresh(fm, co):
    code = co["code"]
    rev = fm.get("TaiwanStockMonthRevenue", code, START)
    eps = fm.get("TaiwanStockFinancialStatements", code, START)
    div = fm.get("TaiwanStockDividend", code, START)
    if rev is None and eps is None:
        return False
    for x in rev or []:
        co["rev"][f"{x['revenue_year']}-{x['revenue_month']:02d}"] = r2(x["revenue"] / 1e8)
    for x in eps or []:
        if x.get("type") == "EPS":
            d = x["date"]
            q = f"{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}"
            co["eps"][q] = r2(x["value"])
            if q in co.get("eps_est", []):
                co["eps_est"].remove(q)
    if div is not None:
        dv = {}
        for x in div:
            y = roc_year(x.get("year"))
            if y:
                dv[str(y)] = dv.get(str(y), 0) + (x.get("CashEarningsDistribution") or 0) + (x.get("CashStatutorySurplus") or 0)
        co["div"] = {k: r2(v, 4) for k, v in sorted(dv.items())}
    co["finmind_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return True


# ---------- derived ----------
def qprev(q, n=1):
    i = int(q[:4]) * 4 + int(q[5]) - 1 - n
    return f"{i // 4}Q{i % 4 + 1}"


def mprev(m, n=1):
    i = int(m[:4]) * 12 + int(m[5:]) - 1 - n
    return f"{i // 12}-{i % 12 + 1:02d}"


def pct(a, b):
    return r2((a - b) / abs(b) * 100) if a is not None and b not in (None, 0) else None


def derive(co, mult):
    d = {}
    rev = co["rev"]
    if rev:
        m = max(rev)
        d.update(latest_month=m, rev=rev[m], mom=pct(rev[m], rev.get(mprev(m))), yoy=pct(rev[m], rev.get(mprev(m, 12))))
        y, mo = int(m[:4]), int(m[5:])
        cur = [rev.get(f"{y}-{i:02d}") for i in range(1, mo + 1)]
        last = [rev.get(f"{y - 1}-{i:02d}") for i in range(1, mo + 1)]
        if None not in cur and None not in last:
            d.update(ytd=r2(sum(cur)), ytd_yoy=pct(sum(cur), sum(last)))
        q3 = [rev.get(mprev(m, i)) for i in range(3)]
        q3p = [rev.get(mprev(m, i + 12)) for i in range(3)]
        if None not in q3 and None not in q3p:
            d["rev3m_yoy"] = pct(sum(q3), sum(q3p))
    eps = co["eps"]
    if eps:
        q = max(eps, key=lambda k: (int(k[:4]), int(k[5])))
        d.update(latest_q=q, eps_q=eps[q], eps_q_est=q in co.get("eps_est", []),
                 eps_qoq=pct(eps[q], eps.get(qprev(q))), eps_yoy=pct(eps[q], eps.get(qprev(q, 4))))
        ttm = [eps.get(qprev(q, i)) for i in range(4)]
        if None not in ttm:
            d["eps_ttm"] = r2(sum(ttm))
        yrs = {}
        for k, v in eps.items():
            yrs.setdefault(k[:4], []).append(v)
        d["eps_year"] = {y: r2(sum(v)) for y, v in yrs.items() if len(v) == 4}
        cy = q[:4]
        ytd = [eps.get(f"{cy}Q{i}") for i in range(1, int(q[5]) + 1)]
        if None not in ytd:
            d["eps_ytd"] = r2(sum(ytd))
            d["eps_est_year"] = r2(sum(ytd) / len(ytd) * 4)  # 今年已公布季年化
            d["target_price"] = r2(d["eps_est_year"] * mult, 1)
    price = co.get("price")
    if price:
        if d.get("eps_ttm") and d["eps_ttm"] > 0:
            d["pe"] = r2(price / d["eps_ttm"])
        divs = co.get("div") or {}
        if divs:
            ly = max(divs)
            d.update(div_year=ly, div=divs[ly], yield_=r2(divs[ly] / price * 100))
        if d.get("target_price"):
            d["upside"] = pct(d["target_price"], price)
    co["d"] = d


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-finmind", action="store_true")
    ap.add_argument("--offline", help="本機測試：fineps/finrev clone 所在資料夾")
    a = ap.parse_args()

    cfg = json.load(open(CONFIG, encoding="utf-8"))
    db = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"companies": {}}
    before = json.dumps(db.get("companies"), sort_keys=True)

    eps_src = [load_src(a.offline, "fineps", f) for f in ("eps-twse.json", "eps-tpex.json")]
    rev_src = [load_src(a.offline, "finrev", f) for f in ("revenue-twse.json", "revenue-tpex.json")]
    prices = load_src(a.offline, "fineps", "prices.json") or {}
    concepts = (load_src(a.offline, "fineps", "stock-concepts.json") or {}).get("map", {})
    fm = FinMind(0 if a.no_finmind else MAX_FINMIND)
    now = dt.datetime.now(dt.timezone.utc)

    active = set()
    for c in cfg["companies"]:
        code = c["code"]
        active.add(code)
        co = db["companies"].setdefault(code, {"code": code, "rev": {}, "eps": {}, "div": {}, "eps_est": []})
        co.update({k: c.get(k) for k in ("name", "group", "products", "note")})
        co["active"] = True
        co["concepts"] = sorted(set(c.get("concepts", [])) | {("0050成分股" if x.startswith("元大台灣50") else x) for x in concepts.get(code, [])})

        # 1) fineps 季 EPS（官方批次 + 搶先報暫估）
        for src in eps_src:
            s = (src or {}).get("stocks", {}).get(code)
            if not s:
                continue
            co["industry"] = s.get("industry") or co.get("industry")
            est = s.get("est", {})
            for k, v in s.get("quarters", {}).items():
                y, q = k.split("_")
                key = f"{y}Q{q}"
                if v is None:
                    continue
                if key not in co["eps"] or key in co["eps_est"]:  # 不覆寫 FinMind 官方值
                    co["eps"][key] = r2(v)
                    if est.get(k):
                        co["eps_est"] = sorted(set(co["eps_est"]) | {key})
                    elif key in co["eps_est"]:
                        co["eps_est"].remove(key)
        # 2) finrev 月營收
        for src in rev_src:
            s = (src or {}).get("stocks", {}).get(code)
            if not s:
                continue
            co["industry"] = co.get("industry") or s.get("industry")
            for k, v in s.get("months", {}).items():
                if v is not None:
                    y, m = k.split("_")
                    co["rev"][f"{y}-{int(m):02d}"] = r2(v / 1e8)
        # 3) 股價
        for mk in ("twse", "tpex"):
            p = prices.get(mk, {}).get("p", {}).get(code)
            if p:
                co["price"], co["chg"], co["price_date"] = p[0], p[1], prices[mk].get("date")
        # 4) FinMind 深度歷史 / 股利（節流）
        last = co.get("finmind_at")
        due = not last or (now - dt.datetime.fromisoformat(last)).total_seconds() > FINMIND_DAYS * 86400
        if due and not fm.dead and fm.calls + 3 <= fm.budget:
            ok = finmind_refresh(fm, co)
            print(f"FinMind {code} {c['name']}: {'ok' if ok else 'fail'}")

    for code, co in db["companies"].items():
        if code not in active:
            co["active"] = False
        co["rev"] = dict(sorted(co["rev"].items()))
        co["eps"] = dict(sorted(co["eps"].items()))
        derive(co, cfg.get("pe_multiple", 20))

    db["groups"] = cfg.get("groups", [])
    db["pe_multiple"] = cfg.get("pe_multiple", 20)
    db["price_date"] = max([p.get("date", "") for p in (prices.get("twse", {}), prices.get("tpex", {}))] or [""])
    if json.dumps(db["companies"], sort_keys=True) != before or "updated_at" not in db:
        db["updated_at"] = now.isoformat(timespec="seconds")
    else:
        print("資料無變動")
    print(f"FinMind calls: {fm.calls}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(db, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(cfg, open(os.path.join(ROOT, "public", "data", "companies.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
