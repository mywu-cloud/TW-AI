#!/usr/bin/env python3
"""tw-ai.json → CSV / 多工作表 Excel（台股慣例：紅=增加/上漲，綠=減少/下跌）"""
import csv
import json
import os

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "public", "data", "tw-ai.json")
EXP = os.path.join(ROOT, "public", "data", "exports")
RED, GREEN = "D7263D", "1B9E4B"
H1 = PatternFill("solid", fgColor="F4A6A0")
H2 = PatternFill("solid", fgColor="9BF0F0")
H3 = PatternFill("solid", fgColor="F59AC8")
H4 = PatternFill("solid", fgColor="FFF27A")
THIN = Side(style="thin", color="AAAAAA")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def qk(q):
    return int(q[:4]) * 4 + int(q[5])


def products(c):
    return "、".join(p["name"] + (f" {p['pct']:g}%" if p.get("pct") is not None else "") for p in c.get("products") or [])


def hdr(ws, fills=None):
    for i, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=True)
        cell.fill = (fills or {}).get(i, H1)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BOX
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "C2"


def posneg(ws, rng):
    ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=RED)))
    ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], font=Font(color=GREEN)))


def fmt(ws, col, n1, n2, f):
    for row in ws[f"{col}{n1}:{col}{n2}"]:
        row[0].number_format = f


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


def main():
    db = json.load(open(DB, encoding="utf-8"))
    mult = db.get("pe_multiple", 20)
    order = {g: i for i, g in enumerate(db.get("groups", []))}
    cos = sorted([c for c in db["companies"].values() if c.get("active", True)],
                 key=lambda c: (order.get(c.get("group"), 99), -(c["d"].get("rev") or 0)))
    months = sorted({m for c in cos for m in c["rev"]})
    quarters = sorted({q for c in cos for q in c["eps"]}, key=qk)
    lm = max((c["d"].get("latest_month") for c in cos if c["d"].get("latest_month")), default=None)
    lq = max((c["d"].get("latest_q") for c in cos if c["d"].get("latest_q")), key=qk, default=None)
    cy = int(lq[:4]) if lq else 2026
    os.makedirs(EXP, exist_ok=True)
    n = len(cos) + 1

    wb = Workbook()
    ws = wb.active
    ws.title = "說明"
    for line in [["台灣 AI 科技財報追蹤"], ["更新時間 (UTC)", db.get("updated_at")], ["股價日期", db.get("price_date")],
                 ["單位", "月營收：億元；EPS：元"], ["資料來源", "FinMind、公開資訊觀測站 / TWSE・TPEx OpenAPI（經 fineps / finrev 快取）"],
                 ["今年預估EPS", "今年已公布各季 EPS 平均 × 4（年化）；價位預估 = 預估EPS × %d 倍" % mult],
                 ["暫估", "最新一季 EPS 若標註「暫估」，為由累計 EPS 推算之搶先數字，官方單季數字公布後自動更新"],
                 ["主要產品", "約略營收比重，取自年報／法說會之概略值，僅供參考，可於 config/companies.json 修正"],
                 ["顏色", "紅色＝成長 / 上漲；綠色＝衰退 / 下跌（台股慣例）"],
                 ["免責聲明", "本資料僅供研究參考，不構成任何投資建議；資料可能延遲或有誤，請以公開資訊觀測站公告為準。"]]:
        ws.append(line)
    ws["A1"].font = Font(bold=True, size=14)
    widths(ws, [14, 90])

    # 月營收總覽（對應附表格式）
    last6 = [m for m in months if m <= lm][-6:] if lm else []
    ws = wb.create_sheet("月營收總覽")
    head = ["代號", "公司", "概念分類", "產業類別", "主要產品(約略比重)"] + last6 + ["月增率(%)", "年增率(%)", "累計年增率(%)",
           f"{cy-2} EPS", f"{cy-1} EPS", "最新現金股利", f"{lq} EPS" if lq else "最新季EPS", "股價", "現金殖利率(%)", "本益比(近4季)"]
    ws.append(head)
    for c in cos:
        d = c["d"]
        ey = d.get("eps_year", {})
        ws.append([c["code"], c["name"], c.get("group"), c.get("industry"), products(c)] + [c["rev"].get(m) for m in last6] +
                  [d.get("mom"), d.get("yoy"), d.get("ytd_yoy"), ey.get(str(cy - 2)), ey.get(str(cy - 1)), d.get("div"),
                   c["eps"].get(lq) if lq else None, c.get("price"), d.get("yield_"), d.get("pe")])
    k = 6 + len(last6)
    hdr(ws, {**{i: H2 for i in range(k + 3, k + 6)}, k + 6: H3, k + 7: H4})
    for i in range(6, k):
        fmt(ws, get_column_letter(i), 2, n, "#,##0.00")
    for i in range(k, k + 3):
        col = get_column_letter(i)
        posneg(ws, f"{col}2:{col}{n}")
        fmt(ws, col, 2, n, '0.0"%"')
    widths(ws, [7, 11, 14, 14, 34] + [11] * len(last6) + [9, 9, 10, 9, 9, 9, 9, 9, 9, 9])

    # EPS 總覽（對應附表 CSV 格式）
    q8 = [q for q in quarters if not lq or qk(q) <= qk(lq)][-8:]
    yrs = [str(y) for y in range(cy - 3, cy)]
    ws = wb.create_sheet("EPS總覽")
    ws.append(["代號", "股票", "概念分類", "股價", "本益比"] + q8 + [f"{y} EPS" for y in yrs] +
              ["最新現金股利", "股利年度", f"{cy} 累計EPS", f"{cy} EPS預估(年化)", f"價位預估({mult}x)", "潛在漲幅(%)", "最新季暫估", "備註"])
    for c in cos:
        d = c["d"]
        ws.append([c["code"], c["name"], c.get("group"), c.get("price"), d.get("pe")] + [c["eps"].get(q) for q in q8] +
                  [d.get("eps_year", {}).get(y) for y in yrs] +
                  [d.get("div"), d.get("div_year"), d.get("eps_ytd"), d.get("eps_est_year"), d.get("target_price"), d.get("upside"),
                   "暫估" if d.get("eps_q_est") else "", c.get("note")])
    hdr(ws)
    for i in range(6, 6 + len(q8) + len(yrs)):
        col = get_column_letter(i)
        posneg(ws, f"{col}2:{col}{n}")
        fmt(ws, col, 2, n, "0.00")
    up = get_column_letter(6 + len(q8) + len(yrs) + 5)
    posneg(ws, f"{up}2:{up}{n}")
    widths(ws, [7, 11, 14, 9, 8] + [8] * (len(q8) + len(yrs)) + [10, 8, 10, 12, 12, 10, 9, 16])

    def pivot(name, keys, getter, f, color=False):
        w = wb.create_sheet(name)
        w.append(["代號", "公司", "概念分類"] + keys)
        for c in cos:
            w.append([c["code"], c["name"], c.get("group")] + [getter(c, x) for x in keys])
        hdr(w)
        rng = f"D2:{get_column_letter(len(keys) + 3)}{n}"
        for row in w[rng]:
            for cell in row:
                cell.number_format = f
        if color:
            posneg(w, rng)
        widths(w, [7, 11, 14] + [10] * len(keys))

    def ryoy(c, m):
        a, b = c["rev"].get(m), c["rev"].get(f"{int(m[:4]) - 1}{m[4:]}")
        return round((a - b) / b * 100, 2) if a is not None and b else None

    pivot("月營收歷史(億元)", months[::-1], lambda c, m: c["rev"].get(m), "#,##0.00")
    pivot("月營收年增率%", months[::-1], ryoy, "0.0", True)
    pivot("季EPS歷史", quarters[::-1], lambda c, q: c["eps"].get(q), "0.00", True)
    ys = sorted({y for c in cos for y in list(c["d"].get("eps_year", {})) + list(c.get("div") or {})})[::-1]
    w = wb.create_sheet("年度EPS與股利")
    w.append(["代號", "公司", "概念分類"] + [f"{y} EPS" for y in ys] + [f"{y} 現金股利" for y in ys])
    for c in cos:
        w.append([c["code"], c["name"], c.get("group")] + [c["d"].get("eps_year", {}).get(y) for y in ys] + [(c.get("div") or {}).get(y) for y in ys])
    hdr(w)
    widths(w, [7, 11, 14] + [10] * len(ys) * 2)
    w = wb.create_sheet("主要產品")
    w.append(["代號", "公司", "概念分類", "產業類別", "概念標籤", "主要產品(約略營收比重)", "備註"])
    for c in cos:
        w.append([c["code"], c["name"], c.get("group"), c.get("industry"), "、".join(c.get("concepts", [])), products(c), c.get("note")])
    hdr(w)
    widths(w, [7, 11, 14, 16, 40, 60, 16])
    wb.save(os.path.join(EXP, "tw-ai.xlsx"))

    # CSV
    def wcsv(fn, head, rows):
        with open(os.path.join(EXP, fn), "w", newline="", encoding="utf-8-sig") as f:
            cw = csv.writer(f)
            cw.writerow(head)
            cw.writerows(rows)
    wcsv("overview.csv", ["代號", "公司", "概念分類", "產業類別", "主要產品", "最新月份", "月營收(億)", "月增率%", "年增率%", "累計營收(億)", "累計年增率%",
                          "最新季", "季EPS", "季EPS暫估", "近4季EPS", f"{cy} 累計EPS", f"{cy} EPS預估", f"價位預估({mult}x)", "股價", "本益比", "現金股利", "殖利率%", "備註"],
         [[c["code"], c["name"], c.get("group"), c.get("industry"), products(c), d.get("latest_month"), d.get("rev"), d.get("mom"), d.get("yoy"),
           d.get("ytd"), d.get("ytd_yoy"), d.get("latest_q"), d.get("eps_q"), "Y" if d.get("eps_q_est") else "", d.get("eps_ttm"), d.get("eps_ytd"),
           d.get("eps_est_year"), d.get("target_price"), c.get("price"), d.get("pe"), d.get("div"), d.get("yield_"), c.get("note")]
          for c in cos for d in [c["d"]]])
    wcsv("revenue_monthly.csv", ["代號", "公司", "月份", "營收(億元)", "年增率%"],
         [[c["code"], c["name"], m, v, ryoy(c, m)] for c in cos for m, v in c["rev"].items()])
    wcsv("eps_quarterly.csv", ["代號", "公司", "季度", "EPS", "暫估"],
         [[c["code"], c["name"], q, v, "Y" if q in c.get("eps_est", []) else ""] for c in cos for q, v in c["eps"].items()])
    print("匯出：", sorted(os.listdir(EXP)))


if __name__ == "__main__":
    main()
