# 台灣AI科技財報（TW-AI）

追蹤台灣電子五哥與主要 AI 供應鏈公司的**月營收**與**季 EPS**，長期趨勢圖、概念分類、主要產品營收比重，可匯出 CSV / Excel。
網站部署於 Cloudflare Pages（輸出目錄 `public/`，無 build 指令）。

## 分頁
| 分頁 | 內容 |
|---|---|
| 月營收總覽 | 近 6 個月營收、月增 / 年增 / 累計年增、前兩年 EPS、現金股利、最新季 EPS、股價、殖利率、本益比 |
| EPS 總覽 | 近 8 季 EPS（含搶先報暫估）、年度 EPS、今年累計與年化預估、價位預估（倍數可調）、潛在空間 |
| 個股趨勢 | 月營收 + 年增率（2019 起）、季 EPS、年度 EPS / 股利 / 配發率、主要產品比重圓餅圖、季度明細 |
| 類股比較 | 月營收年增率、月營收、季 EPS、EPS 年增率 — 個股或概念分類加總熱力圖 + 走勢 |
| 追蹤名單 | 本機顯示 / 隱藏、永久新增 / 刪除說明 |

## 資料來源與更新
GitHub Actions 每日 4 次（台灣時間 09:13、14:13、20:13、23:13）：
1. **mywu-cloud/fineps**：全市場季 EPS（含累計推算之「暫估」）、收盤價、概念標籤
2. **mywu-cloud/finrev**：全市場月營收（近 2 年）
3. **FinMind**（每檔每 7 天一次）：2019 年起月營收、季 EPS 官方值、現金股利。
   無 token 每小時約 300 次；建議在 repo **Settings → Secrets → Actions** 新增 `FINMIND_TOKEN`。

## 新增 / 刪除公司
**最簡單：網站「追蹤名單」分頁的管理表單**（填代號 / 名稱 / 分類 / 產品比重，或在名單按「移除」→ 輸入管理密碼 → 送出）。
表單呼叫 Cloudflare Pages Function `functions/api/manage.js`，由它代為觸發下方 workflow；GitHub token 只存在 Cloudflare，不會出現在前端。
一次性設定（Cloudflare Pages → Settings → Variables and Secrets，Production，類型 **Secret**）：
- `GH_TOKEN`：GitHub fine-grained token，Repository access 只選 `mywu-cloud/TW-AI`，權限 **Actions: Read and write**
- `ADMIN_PASSWORD`：管理密碼（建議 16 字以上）

設定後需重新部署一次（Deployments → 最新一筆 → Retry deployment）才會生效。

其他方式：
- Actions → **Update TW-AI** → Run workflow
  - `add`：`代號|名稱|概念分類|產品:比重;產品:比重|備註`，多筆以 `#` 分隔（名稱之後皆可省略；代號已存在則更新有填欄位）
    例：`2345|智邦|光通訊/網通|交換器:85;其他:15#3661|世芯-KY|IC設計/ASIC`
  - `remove`：`2402,4420`
- 或直接編輯 `config/companies.json`（概念分類 `groups`、價位預估倍數 `pe_multiple`、主要產品比重、備註）。

刪除的公司歷史保留（`active:false`），重新加入可延續。主要產品比重為**約略值**，請依最新年報 / 法說會修正。

## 計算口徑
- 月營收單位：億元；累計年增率 = 今年 1 月至最新月 vs 去年同期
- 今年 EPS 預估 = 今年已公布各季平均 × 4；價位預估 = 預估 EPS × 倍數（預設 20）
- 本益比 = 股價 ÷ 近 4 季 EPS；殖利率 = 最新年度現金股利 ÷ 股價

## 本機
```bash
pip install openpyxl
python scripts/fetch.py && python scripts/export.py
python -m http.server -d public
```

> ⚠️ 資料僅供研究參考，不構成投資建議；請以公開資訊觀測站公告為準。
