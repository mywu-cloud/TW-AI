#!/usr/bin/env python3
"""新增 / 刪除追蹤公司
add：代號|名稱|概念分類|產品:比重;產品:比重|備註   多筆以 # 分隔（名稱之後皆可省略）
  python scripts/manage.py --add "2345|智邦|光通訊/網通|交換器:85;其他:15" --remove "2402,4420"
"""
import argparse, json, os
CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "companies.json")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", default="")
    ap.add_argument("--remove", default="")
    a = ap.parse_args()
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    cos = cfg["companies"]
    for spec in [s.strip() for s in a.add.split("#") if s.strip()]:
        p = [x.strip() for x in spec.split("|")] + [""] * 5
        code = p[0]
        if not code.isdigit():
            raise SystemExit(f"代號格式錯誤：{code}")
        prods = []
        for x in [x for x in p[3].split(";") if x.strip()]:
            n, _, pct = x.partition(":")
            prods.append({"name": n.strip(), "pct": float(pct) if pct.strip() else None})
        new = {"code": code, "name": p[1] or code, "group": p[2] or "其他", "products": prods, "note": p[4]}
        old = next((c for c in cos if c["code"] == code), None)
        if old:  # 已存在 → 更新有填的欄位
            for k, i in (("name", 1), ("group", 2), ("note", 4)):
                if p[i]:
                    old[k] = new[k]
            if prods:
                old["products"] = prods
            print("更新", code)
        else:
            cos.append(new)
            print("新增", code, new["name"])
        if new["group"] not in cfg["groups"]:
            cfg["groups"].insert(len(cfg["groups"]) - 1, new["group"])
    for code in [x.strip() for x in a.remove.replace("#", ",").split(",") if x.strip()]:
        n = len(cos)
        cos[:] = [c for c in cos if c["code"] != code]
        print("刪除" if len(cos) < n else "找不到", code)
    json.dump(cfg, open(CONFIG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
