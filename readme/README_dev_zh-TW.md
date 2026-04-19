# 噗浪圖片備份工具 CT — 開發者說明

---

## 環境需求

### Python

需要 **Python 3.10 以上版本**。

請至 [https://www.python.org](https://www.python.org) 下載安裝。

### tkinter

tkinter 是 Python 標準函式庫的一部分，但在部分 Linux 系統上需要另外安裝。

| 平台 | tkinter 安裝方式 |
|---|---|
| Ubuntu / Debian | `sudo apt install python3-tk` |
| Fedora | `sudo dnf install python3-tkinter` |
| macOS | 從 [python.org](https://www.python.org) 安裝 Python，已內含 tkinter |
| Windows | tkinter 已內建於標準 Python 安裝程式中 |

---

## 環境設定

### 1. 複製repo

```bash
git clone https://github.com/rkwithb/Plurk-Image-Backup-Tool-CT.git
cd Plurk-Image-Backup-Tool-CT
```

### 2. 建立虛擬環境（建議）

```bash
python -m venv .venv

# 啟動 — Linux / macOS
source .venv/bin/activate

# 啟動 — Windows
.venv\Scripts\activate
```

### 3. 安裝相依套件

```bash
pip install -r requirements.txt
```

相依套件包含：`customtkinter`、`requests`、`piexif` 及其傳遞相依項目。
`piexif` 在執行時為選用套件，沒有安裝也能正常執行，但 EXIF 補寫功能將無法使用。

---

## 從原始碼執行

### GUI 模式

```bash
python ui/app.py
```

### CLI 模式

```bash
python main.py
```

CLI 模式預期備份資料位於：
- `data/plurks/` — 主噗的 JS 檔案
- `data/responses/` — 回應的 JS 檔案

輸出結果會寫入目前工作目錄下的 `plurk_images_by_date/`。

CLI 模式的目錄結構如下：

```
Plurk-Image-Backup-Tool-CT/
├── main.py                        ← 從這裡執行
├── ... （其他專案檔案）
├── your-plurk-backup/             ← 你的備份資料夾（名稱不限），放在這裡
│   └── data/
│       ├── plurks/
│       └── responses/
└── plurk_images_by_date/          ← 首次執行時自動產生
    └── 2021-03-15/
        └── image.jpg
```

#### 語言參數

CLI 預設使用 `config.json` 中儲存的語言（首次執行預設為 `zh_TW`）。
可使用 `--lang` 參數覆蓋，同時會將選擇儲存供後續執行使用：

```bash
python main.py --lang en
python main.py --lang zh_TW
```

---

## 專案結構

```
Plurk-Image-Backup-Tool-CT/
├── main.py                  # CLI 入口點
├── requirements.txt         # Python 相依套件
├── config.json              # 語言設定儲存檔
│
├── ui/
│   └── app.py               # GUI 入口點（customtkinter）
│
├── core/
│   ├── processor.py         # 協調預掃描與完整備份流程
│   ├── parser.py            # 解析噗浪 JS 備份檔，擷取圖片網址
│   ├── downloader.py        # 下載圖片，含速率限制與退避機制
│   ├── exif_handler.py      # 將 EXIF 時間戳寫入 JPEG 檔案（piexif）
│   ├── i18n.py              # 輕量 i18n — 載入 locale JSON，t() 輔助函式
│   └── logger.py            # 單例檔案記錄器，session 標頭，shutdown 處理
│
├── locales/
│   ├── en.json              # 英文翻譯
│   └── zh_TW.json           # 繁體中文翻譯
│
└── readme/
    ├── README_user_en.md
    ├── README_user_zh-TW.md
    ├── README_dev_en.md
    └── README_dev_zh-TW.md
```

### 主要設計說明

`core/logger.py` 使用行緩衝檔案 I/O（`buffering=1`），讓每行日誌在寫入後立即刷新至磁碟，確保在程式崩潰或強制終止時不會遺失記錄。

`core/downloader.py` 追蹤每個網域的連續失敗次數，並在收到 HTTP 429 回應時自動套用退避延遲，避免對伺服器造成過度請求。

`core/i18n.py` 採用扁平鍵值 JSON 架構，所有 UI 字串皆透過 `t("key")` 存取。語言設定儲存於 `config.json` 並在下次啟動時重新載入。GUI 在切換語言時會透過 `os.execv` 重新啟動程序以套用變更。

---

## 授權條款

本專案採用 [Apache License 2.0](https://creativecommons.org/licenses/by-nc/4.0/) 授權，僅限非商業使用。

> 免責聲明：使用風險自負，作者不對任何損失負責。
