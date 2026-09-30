# Jim Mono TC

等寬字型，同時給本機 terminal 與網頁使用。

| 範圍 | 來源 | 寬度 |
| --- | --- | --- |
| Latin / ASCII | [Hack](https://github.com/source-foundry/Hack) 3.003 | 1 cell (`W`) |
| Programming ligatures（`calt`） | 本專案自繪（`=>` `->` `<-` `==` `===` `!=` `!==`） | 與來源字元同寬 |
| Nerd Font icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) 3.4.0 `--mono` | 1 cell |
| CJK / 全形標點 / 假名 / 注音 | [Noto Sans CJK TC](https://github.com/notofonts/noto-cjk) 2.004（完整：Noto 有的 East Asian Wide/Fullwidth 碼位，約 43,000 個） | 2 cells (`2W`) |
| Emoji | 系統 fallback，不併入 | – |

`W` 是 Hack 半形字元的 advance width（2048 UPM 下為 1233），一個 CJK 全形字元的
advance 恰為 `2W`。授權見 [NOTICE.md](NOTICE.md)。

## 建構

需要 Python 3.10+、FontForge（Nerd Fonts 的 `font-patcher` 需要）、`curl`、`unzip`、`git`。
`hb-shape`（HarfBuzz CLI）可選，有安裝時 `verify.py` 會額外用它交叉驗證。

```sh
python3 -m pip install -r requirements.txt
scripts/build.sh                 # -> dist/JimMonoTC-Regular.{otf,woff2,css}   (OpenType/CFF)
scripts/build.sh --split-web     # WOFF2 依 unicode-range 分片（見「網頁使用」）
scripts/build.sh --format ttf    # 改輸出 TrueType（二次曲線；Hack 的 hinting 保留在 Latin）
```

選項：

* `--format otf|ttf`：預設 `otf`（CFF）。Noto 的三次曲線原樣搬入、Hack / Nerd Fonts 的二次曲線
  精確升階為三次，沒有任何曲線被近似。`ttf` 則把 Noto 以 Cu2Qu 近似成二次曲線。
* `--charset all|big5-common|big5|FILE`：要併入的 CJK 字集。預設 `all`（Noto 有的全部 wide 碼位，
  約 43,000 個碼位、42,779 個 glyph，整個字型 54,757 個 glyph，低於 65,535 的上限）；
  `big5-common`（約 5,900 碼位）、`big5`（約 13,500 碼位）可縮小成品；`FILE` 為純文字檔
  （字元或 `U+XXXX[-YYYY]`）。假名、注音、全形標點一律會併入。
* `--cjk-scale N`：CJK 字面相對 em 的大小，預設 `1.0`（字面完全落在 Hack 的
  ascent / descent 內）。Hack 的半形較寬，想讓漢字看起來更飽滿可試 `1.1`，但注意上下緣可能超出行高。

首次執行會下載並以 SHA-256 驗證固定版本的輸入（`sources/versions.env`、
`sources/checksums.sha256`）到 `.cache/`；Noto 檔案約 16 MB。完整 CJK 的建構約 8 分鐘
（font-patcher 約 1 分鐘、CJK 合併約 2 分鐘、`--split-web` 切片約 2 分鐘）。

### Pipeline

```text
Hack ─► add-ligatures.py ─► font-patcher --complete --mono ─► merge-cjk.py ─► finalize.py ─► verify.py
                                                                                └─► build-web.py (WOFF2 subset)
```

* `add-ligatures.py`：自繪 ligature outline，寫成 `calt`，合併進 Hack 既有的 GSUB。
  每個來源字元仍對應一個 `W` 寬的 glyph（前面的 cell 換成空的 `lig.spacer`，最後一個 cell
  的 glyph 往左延伸），因此有沒有 shaping 總寬度都是 `N × W`，逐 cell 繪製的 terminal 也能用。
* `font-patcher`：Nerd Fonts 官方腳本。
* `merge-cjk.py`：只補 Hack / Nerd 沒有的全形字元，縮放到同一 UPM、置中於 `2W`；`otf` 時整個字型
  改寫成 CFF（外框方向一併反轉為 CFF 的逆時針）。另外還原 patcher 弄寬的零寬組合符號，並取消對應 emoji 寬度碼位的單 cell icon
  （U+25FD、U+25FE、U+26A1）。
* `finalize.py`：新 family name（含 CFF 內部名稱）、`OS/2.xAvgCharWidth = W`、monospaced panose、清掉過時表。
  `--subroutinize` 可用 compreffor 壓縮 CFF charstring，但 5 萬多 glyph 時極慢（本機超過 40 分鐘 CPU 仍未完成），預設關閉。
* `build-web.py`：一律由完成的主字型（OTF / TTF）產生 WOFF2，保證 metrics 與 feature 一致。

## 驗證

`scripts/verify.py dist/JimMonoTC-Regular.otf`（WOFF2 分片用 `--partial`）（`build.sh` 最後會自動執行）：

* 所有 glyph advance 只可能是 `0`、`W`、`2W`；East Asian Wide/Fullwidth 碼位必為 `2W`，其餘為 `W`
* CJK outline 不超出 `2W` cell
* `tests/width-cases.txt`：`A`=1、`中`=2、`中文`=4、`=>`=2、`!=`=2、`===`=3、Nerd icon=1 cell 等，
  分別在 calt 開 / 關時以 HarfBuzz shaping 量總 advance
* `tests/shaping.txt`：ligature 確實被替換（glyph 序列）且總 advance 不變
* `calt` 可由 `DFLT`、`latn` script 觸達；name table 不含 Hack / Noto / Bitstream / Vera / Nerd

手動看瀏覽器渲染：建構後開 `tests/preview.html`（粉紅直條 = 每個 cell）。

## 網頁使用

```css
@font-face {
  font-family: "Jim Mono TC";
  src: url("/fonts/JimMonoTC-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

pre, code, .terminal {
  font-family: "Jim Mono TC", monospace;
  font-variant-ligatures: contextual;
}
```

`build-web.py` 也會產生 `dist/JimMonoTC-Regular.css`；`--url-prefix` 可改字型 URL 前綴
（`build.sh` 用預設 `/fonts/`）。

`--split-web` 把字集依使用頻率切成多個 WOFF2，`unicode-range` 讓瀏覽器只下載頁面用到的分片，
所有分片共用同一個 family name，因此 `2W` 對齊不變：

| 分片 | 內容 | 約略大小 |
| --- | --- | --- |
| `latin` | Hack（含 ligature） | 86 KiB |
| `icons` | Nerd Fonts 圖示（私用區） | 1.3 MB |
| `cjk-common` | Big5 常用字、假名、注音、全形標點 | 1.0 MB |
| `cjk-big5` | Big5 次常用字 | 1.4 MB |
| `cjk-1`…`cjk-12` | 其餘 wide 碼位（各 2,500 碼位，`--slice-size` 可調） | 130–520 KiB |

`src` 只列出 `woff2` 分片；整份 CSS 由 `dist/JimMonoTC-Regular.css` 提供（因 `unicode-range` 列得很細，約 130 KB）。

## Terminal 使用

安裝 `dist/JimMonoTC-Regular.otf`（約 14 MB，含完整 CJK），terminal 的字型設為 `Jim Mono TC`。
需要支援 OpenType shaping 的 terminal（如 WezTerm、Kitty、Windows Terminal）才會顯示 ligature；
不支援時寬度依然正確，只是不顯示 ligature glyph。

## 已知限制與後續

* **Hinting**：CFF 版沒有 TrueType 指令（Noto 的 CFF hint 與新增的 ligature / CJK glyph 本來就不帶）。
  macOS 與高 DPI 螢幕不受影響；Windows 低 DPI 的小字級（約 9–14 px）可能較不銳利。
  需要 Hack 的 TrueType hinting 時用 `--format ttf`（且 CJK 為二次曲線近似）。
* CFF 未做 subroutinize，OTF 約 14 MB（見 `finalize.py --subroutinize`）。
* 完整 CJK 單一字型即可容納（54,757 glyph），所以桌面端不需拆成多個字型；拆分只用於網頁分片。
  若之後加上 Nerd Fonts 以外的字集或 Bold/Italic 同 family，仍各自獨立、各有 65,535 上限。
* 尚未做：
  * Bold / Italic（Hack 有對應字重，Noto 需搭配 Bold）
  * 在實際 terminal（Windows Terminal、WezTerm、Kitty…）與 Firefox 上的實機測試
  * 更多 ligature（`>=` `<=` `<->` `::` `//` 等）
  * Hack 與 Nerd Fonts 各 glyph set 授權的逐項清點（見 NOTICE.md）
