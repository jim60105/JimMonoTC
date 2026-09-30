# Jim Mono TC

等寬字型，同時給本機 terminal 與網頁使用。

| 範圍 | 來源 | 寬度 |
| --- | --- | --- |
| Latin / ASCII | [Hack](https://github.com/source-foundry/Hack) 3.003 | 1 cell (`W`) |
| Programming ligatures（`calt`） | 本專案自繪（`=>` `->` `<-` `==` `===` `!=` `!==`） | 與來源字元同寬 |
| Nerd Font icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) 3.4.0 `--mono` | 1 cell |
| CJK / 全形標點 / 假名 / 注音 | [Noto Sans CJK TC](https://github.com/notofonts/noto-cjk) 2.004 | 2 cells (`2W`) |
| Emoji | 系統 fallback，不併入 | – |

`W` 是 Hack 半形字元的 advance width（2048 UPM 下為 1233），一個 CJK 全形字元的
advance 恰為 `2W`。授權見 [NOTICE.md](NOTICE.md)。

## 建構

需要 Python 3.10+、FontForge（Nerd Fonts 的 `font-patcher` 需要）、`curl`、`unzip`、`git`。
`hb-shape`（HarfBuzz CLI）可選，有安裝時 `verify.py` 會額外用它交叉驗證。

```sh
python3 -m pip install -r requirements.txt
scripts/build.sh                 # -> dist/JimMonoTC-Regular.{ttf,woff2,css}
scripts/build.sh --split-web     # WOFF2 依 unicode-range 分成 latin / cjk 兩個檔
```

選項：

* `--charset big5-common|big5|FILE`：要併入的 CJK 字集。預設 `big5-common`
  （Big5 常用字約 5,400 字 + 符號，共 5,891 個碼位），`big5` 為整個 Big5 字集（約 13,000 漢字，約 13,500 碼位、TTF 約 7.7 MB）；`FILE` 為純文字檔
  （字元或 `U+XXXX[-YYYY]`）。假名、注音、全形標點一律會併入。
* `--cjk-scale N`：CJK 字面相對 em 的大小，預設 `1.0`（字面完全落在 Hack 的
  ascent / descent 內）。Hack 的半形較寬，想讓漢字看起來更飽滿可試 `1.1`，但注意上下緣可能超出行高。

首次執行會下載並以 SHA-256 驗證固定版本的輸入（`sources/versions.env`、
`sources/checksums.sha256`）到 `.cache/`；Noto 檔案約 16 MB。約 2 分鐘完成，
其中 font-patcher 佔一半以上。

### Pipeline

```text
Hack ─► add-ligatures.py ─► font-patcher --complete --mono ─► merge-cjk.py ─► finalize.py ─► verify.py
                                                                                └─► build-web.py (WOFF2 subset)
```

* `add-ligatures.py`：自繪 ligature outline，寫成 `calt`，合併進 Hack 既有的 GSUB。
  每個來源字元仍對應一個 `W` 寬的 glyph（前面的 cell 換成空的 `lig.spacer`，最後一個 cell
  的 glyph 往左延伸），因此有沒有 shaping 總寬度都是 `N × W`，逐 cell 繪製的 terminal 也能用。
* `font-patcher`：Nerd Fonts 官方腳本。
* `merge-cjk.py`：只補 Hack / Nerd 沒有的全形字元；CFF → TrueType 二次曲線，縮放到同一 UPM，
  置中於 `2W`。另外還原 patcher 弄寬的零寬組合符號，並取消對應 emoji 寬度碼位的單 cell icon
  （U+25FD、U+25FE、U+26A1）。
* `finalize.py`：新 family name、`OS/2.xAvgCharWidth = W`、monospaced panose、清掉過時表。
* `build-web.py`：一律由完成的 TTF 產生 WOFF2，保證 metrics 與 feature 一致。

## 驗證

`scripts/verify.py dist/JimMonoTC-Regular.ttf dist/JimMonoTC-Regular.woff2`（`build.sh` 最後會自動執行）：

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

`build-web.py` 也會產生 `dist/JimMonoTC-Regular.css`（`--split` 時含 `unicode-range`）；
`--url-prefix` 可改字型 URL 前綴（`build.sh` 用預設 `/fonts/`）。

## Terminal 使用

安裝 `dist/JimMonoTC-Regular.ttf`，terminal 的字型設為 `Jim Mono TC`。
需要支援 OpenType shaping 的 terminal（如 WezTerm、Kitty、Windows Terminal）才會顯示 ligature；
不支援時寬度依然正確，只是不顯示 ligature glyph。

## 目前範圍與後續

這是最小 prototype：只有 Regular、CJK 為有限字集、單一 TTF。尚未做：

* Bold / Italic（Hack 有對應字重，Noto 需搭配 Bold）
* 完整 CJK 範圍。Noto CJK 本身就接近 TrueType 65,535 glyph 上限，加上 Nerd Fonts 的約 1.2 萬個 icon
  無法放進單一 TTF，需縮減字集、去掉不用的 icon glyph set，或改輸出 CFF 版 OTF
* 在實際 terminal（Windows Terminal、WezTerm、Kitty…）與 Firefox 上的實機測試
* 更多 ligature（`>=` `<=` `<->` `::` `//` 等）
* Hack 與 Nerd Fonts 各 glyph set 授權的逐項清點（見 NOTICE.md）
