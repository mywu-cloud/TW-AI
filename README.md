# 台灣AI科技公司財報（TW-AI）

追蹤台灣電子五哥與主要 AI 供應鏈公司的**月營收**與**季 EPS**，長期趨勢圖、概念分類、主要產品營收比重，可匯出 CSV / Excel。
網站部署於 Cloudflare Pages（輸出目錄 `public/`，無 build 指令）。

## 分頁
| 分頁 | 內容 |
|---|---|
| 月營收總覽 | 近 6 個月營收、月增 / 年增 / 累計年增、前兩年 EPS、現金股利、最新季 EPS、股價、殖利率、本益比 |
| EPS 總覽 | 近 8 季 EPS（含搶先報暫估）、年度 EPS、今年累計與年化預估、價位預估（倍數可調）、潛在空間 |
| 個股趨勢 | 月營收 + 年增率（2019 起）、季 EPS、年度 EPS / 股利 / 配發率、主要產品比重圓餅圖、季度明細 |
| 類股比較 | 月營收年增率、月營收、季 EPS、EPS 年增率 — 個股或概念分類加總熱力圖 + 走勢 |
| 追蹤名單 | 本機顯示 / 隱藏、快速新增（自動帶名稱）、移除 / 重新加入、管理表單（密碼保護，永久新增 / 刪除） |

## 資料來源與更新
GitHub Actions 每日 4 次（台灣時間 09:13、14:13、20:13、23:13）：
1. **mywu-cloud/fineps**：全市場季 EPS（含累計推算之「暫估」）、收盤價、概念標籤
2. **mywu-cloud/finrev**：全市場月營收（近 2 年）
3. **FinMind**（每檔每 7 天一次）：2019 年起月營收、季 EPS 官方值、現金股利。
   無 token 每小時約 300 次；建議在 repo **Settings → Secrets → Actions** 新增 `FINMIND_TOKEN`。

產出檔案（`public/data/`）：`tw-ai.json`（網站主資料）、`companies.json`（名單設定副本）、`names.json`（全市場代號 → 名稱 / 產業，供快速新增）、`exports/`（CSV / Excel）。

## 新增 / 刪除公司

### 網站操作（建議）
在網站「**追蹤名單**」分頁：

| 動作 | 操作 |
|---|---|
| 新增 | 上方「**快速新增**」輸入代號或名稱（下拉選單含全市場約 2,150 檔，名稱自動帶出），可填概念分類 → 按「＋ 加入」或 Enter；或直接在下方表單填一列（代號 / 名稱 / 概念分類 / 主要產品:比重 / 備註），按「＋ 再加一列」可多筆 |
| 刪除 | 名單第 2 欄按「**移除**」；或先取消勾選數家，再按「**取消勾選的 → 排入刪除**」一次加入 |
| 重新加入 | 已移除公司第 2 欄按「**重新加入**」（帶出原名稱與分類） |
| 送出 | 下方輸入**管理密碼** → 「送出」→ 確認；約 3–10 分鐘後重新整理即可看到。「查看執行狀態」可看最近 5 次執行結果 |

- 僅「取消勾選」＝只在自己瀏覽器隱藏（存 localStorage），**不會**刪除。
- 代號已存在 → 只更新有填的欄位。未填名稱 → 更新時由 fetch.py 依 `names.json` 自動補上。
- 主要產品比重格式：`交換器:85;其他:15`（全形「：；」會自動轉半形）。

### 運作方式
```
網站表單 ──POST /api/manage──▶ Cloudflare Pages Function（functions/api/manage.js）
                                 │ 驗證 ADMIN_PASSWORD
                                 ▼
               GitHub API：觸發 workflow_dispatch「Update TW-AI」（inputs: add / remove）
                                 ▼
          scripts/manage.py 改 config/companies.json → fetch.py 抓資料 → export.py → commit
                                 ▼
                     Cloudflare Pages 自動重新部署
```
GitHub token 只存在 Cloudflare Secret，不會出現在前端；沒有密碼無法送出。
`GET /api/manage`（header `X-Admin-Password`）回傳最近 5 次手動執行狀態。

### 一次性設定
1. **GitHub token**：個人頭像 → Settings → Developer settings → Personal access tokens → **Fine-grained tokens**（或直接開 <https://github.com/settings/personal-access-tokens/new>）
   - Repository access：**Only select repositories** → `mywu-cloud/TW-AI`
   - Repository permissions：**Actions: Read and write**（其他不用開）
2. **Cloudflare Pages** → tw-ai → 設定 → 變數與機密（**Production**），類型 **Secret**：
   - `GH_TOKEN`：上一步的 token（`github_pat_` 開頭）
   - `ADMIN_PASSWORD`：管理密碼（建議 16 字以上；區分大小寫）
   - 選填：`GH_REPO`（預設 `mywu-cloud/TW-AI`）、`GH_WORKFLOW`（預設 `update.yml`）、`GH_REF`（預設 `main`）
3. **重新部署**：部署 → 最新一筆「⋯」→ **重試部署**。⚠️ 變數只套用到之後的部署，**每次修改變數都要重新部署**（或推一個 commit）。

### 疑難排解
| 訊息 | 原因 / 處理 |
|---|---|
| 伺服器尚未設定 GH_TOKEN / ADMIN_PASSWORD | 變數未設定、設在 Preview、名稱拼錯，或設定後尚未重新部署 |
| 密碼錯誤（你輸入了 N 個字元） | 與 `ADMIN_PASSWORD` 不符。比對前兩邊都會去前後空白 / 換行 / 外層引號、全形轉半形，但**區分大小寫**。核對字數；避免瀏覽器自動填入別的密碼；改密碼後記得重新部署 |
| GitHub 回應 401 | token 過期或錯誤 → 重新產生並更新 `GH_TOKEN`，再重新部署 |
| GitHub 回應 403 / 404 | token 沒選到 TW-AI 或 Actions 權限不是 Read and write |
| 執行失敗（查看執行狀態 ❌） | 點「詳細」看 Actions log；常見為代號格式錯誤 |

### 備用方式（不經網站）
- GitHub → Actions → **Update TW-AI** → Run workflow
  - `add`：`代號|名稱|概念分類|產品:比重;產品:比重|備註`，多筆以 `#` 分隔（名稱之後皆可省略；代號已存在則更新有填欄位）
    例：`2345|智邦|光通訊/網通|交換器:85;其他:15#3661|世芯-KY|IC設計/ASIC`
  - `remove`：`2402,4420`
- 或直接編輯 `config/companies.json`（概念分類 `groups`、價位預估倍數 `pe_multiple`、主要產品比重、備註）。

刪除的公司歷史保留（`active:false`），重新加入可延續。主要產品比重為**約略值**，請依最新年報 / 法說會修正。

## 計算口徑
- 月營收單位：億元；累計年增率 = 今年 1 月至最新月 vs 去年同期
- 今年 EPS 預估 = 今年已公布各季平均 × 4；價位預估 = 預估 EPS × 倍數（預設 20）
- 本益比 = 股價 ÷ 近 4 季 EPS；殖利率 = 最新年度現金股利 ÷ 股價

## 檔案結構
| 路徑 | 說明 |
|---|---|
| `public/index.html` | 網站（單檔 HTML + Chart.js） |
| `functions/api/manage.js` | Cloudflare Pages Function：管理表單後端 |
| `config/companies.json` | 追蹤名單設定 |
| `scripts/manage.py` | 新增 / 刪除名單（workflow 呼叫） |
| `scripts/fetch.py` | 抓 fineps / finrev / FinMind，產生 `tw-ai.json`、`names.json` |
| `scripts/export.py` | 匯出 CSV / Excel |
| `.github/workflows/update.yml` | 每日 4 次排程 + 手動新增 / 刪除 |

## 本機
```bash
pip install openpyxl
python scripts/fetch.py && python scripts/export.py
python -m http.server -d public
```

> ⚠️ 資料僅供研究參考，不構成投資建議；請以公開資訊觀測站公告為準。
