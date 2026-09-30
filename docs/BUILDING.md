# 開發與建構指南

給想自己建構、修改或除錯 Jim Mono TC 的人。一般使用請看 [README](../README.md)。

## 建構

需要 Python 3.10+、FontForge（Nerd Fonts 的 `font-patcher` 需要）、`curl`、`unzip`、`git`。
`hb-shape`（HarfBuzz CLI）可選，有安裝時 `verify.py` 會額外用它交叉驗證。

```sh
python3 -m pip install -r requirements.txt
scripts/build.sh                 # -> dist/JimMonoTC-{Regular,Bold,Italic,BoldItalic}.{otf,woff2}, JimMonoTC.css
scripts/build.sh --split-web     # WOFF2 依 unicode-range 分片（見「網頁使用」）
scripts/build.sh --format ttf    # 改輸出 TrueType（二次曲線；Hack 的 hinting 保留在 Latin）
```

選項：

* `--styles "Regular Bold"`：只建構部分樣式，預設四種全建。
* `--format otf|ttf`：預設 `otf`（CFF）。Noto 的三次曲線原樣搬入、Hack / Nerd Fonts 的二次曲線
  精確升階為三次，沒有任何曲線被近似。`ttf` 則把 Noto 以 Cu2Qu 近似成二次曲線。
* `--charset all|big5-common|big5|FILE`：要併入的 CJK 字集。預設 `all`（Noto 有的全部 wide 碼位，
  約 43,000 個碼位、42,779 個 glyph，整個字型 54,757 個 glyph，低於 65,535 的上限）；
  `big5-common`（約 5,900 碼位）、`big5`（約 13,500 碼位）可縮小成品；`FILE` 為純文字檔
  （字元或 `U+XXXX[-YYYY]`）。假名、注音、全形標點一律會併入。
* `--cjk-scale N`：CJK 字面相對 em 的大小，預設 `1.0`（字面完全落在 Hack 的
  ascent / descent 內）。Hack 的半形較寬，想讓漢字看起來更飽滿可試 `1.1`，但注意上下緣可能超出行高。

首次執行會下載並以 SHA-256 驗證固定版本的輸入（`sources/versions.env`、
`sources/checksums.sha256`）到 `.cache/`；Noto 檔案約 16 MB。完整 CJK 的單一樣式約 8 分鐘
（font-patcher 約 1 分鐘、CJK 合併約 2 分鐘），四種樣式約 30 分鐘；`--split-web` 約 270 個切片，每個樣式再多約 10 分鐘。

### Pipeline

```text
Hack ─► add-ligatures.py ─► font-patcher --complete --mono ─► merge-cjk.py ─► finalize.py ─► verify.py
                                                                                └─► build-web.py (WOFF2 subset)
```

* `add-ligatures.py`：自繪 ligature outline，寫成 `calt`，合併進 Hack 既有的 GSUB。線條粗細與箭頭頭部都從各樣式
  Hack 的 `=`、`>` 量測，Bold 自動變粗；Hack Italic 的 `=`、`>` 本來就不傾斜，所以斜體的連字也維持直立。
  每個來源字元仍對應一個 `W` 寬的 glyph（前面的 cell 換成空的 `lig.spacer`，最後一個 cell
  的 glyph 往左延伸），因此有沒有 shaping 總寬度都是 `N × W`，逐 cell 繪製的 terminal 也能用。
* `font-patcher`：Nerd Fonts 官方腳本。
* `merge-cjk.py`：只補 Hack / Nerd 沒有的全形字元，縮放到同一 UPM、置中於 `2W`（Italic 依 Hack 的 `italicAngle` 以行中線為軸斜切，
  少數撐滿格子的字元，如 U+FFE3，斜切後會平移回格內）；`otf` 時整個字型
  改寫成 CFF（外框方向一併反轉為 CFF 的逆時針）。另外還原 patcher 弄寬的零寬組合符號，並取消對應 emoji 寬度碼位的單 cell icon
  （U+25FD、U+25FE、U+26A1）。
* `finalize.py`：新 family name（含 CFF 內部名稱）、依樣式設定 `usWeightClass` / `fsSelection` / `macStyle`、`OS/2.xAvgCharWidth = W`、monospaced panose、清掉過時表。
  `--subroutinize` 可用 compreffor 壓縮 CFF charstring，但 5 萬多 glyph 時極慢（本機超過 40 分鐘 CPU 仍未完成），預設關閉。
* `build-web.py`：一律由完成的主字型（OTF / TTF）產生 WOFF2，保證 metrics 與 feature 一致（見下節「網頁分片」）。

### 網頁分片

`build-web.py --split`（`build.sh --split-web`）把 cmap 切成互斥、合起來涵蓋整個 cmap（扣掉 U+0000、U+000D、U+FEFF）的群組。
群組名稱是對外介面（下游專案依名稱挑選），不要改名：

* `latin`、`latin-ext`、`greek-cyrillic`、`box`、`symbols`：單格寬、非私用區的碼位，依 `build-web.py` 內 `WINDOWS` 的順序先到先得。
  落在所有 window 之外的單格碼位會讓建構失敗（要刻意擴充 window，不會默默丟字）。`latin` 帶 `calt` 與連字用到的字元。
* `icons-<N>`：私用區（U+E000–F8FF、第 15–16 面），依大小分塊，`N` 從 1 起算。
* `cjk-<N>`：雙格寬（East Asian Wide / Fullwidth）碼位中，落在 Noto Sans TC Google Fonts 頻率分片 `N` 內者，依檔案順序先到先得，空的分片省略。
  `N` 是 Google 的編號，不是流水號。分片範圍放在 `sources/noto-sans-tc-web-ranges.txt`（內有出處與日期），
  更新時重新從 Google Fonts CSS API 擷取（帶 woff2 的 User-Agent，保留 `.<N>.woff2` 有編號的規則，順序不可變）。
* `cjk-x<N>`：其餘雙格寬碼位，依碼位順序分塊，`N` 從 1 起算。

每個 `.woff2` 不得超過 65,536 bytes（`--max-bytes`），超過就建構失敗。`icons-*` 與 `cjk-x*` 依大小分塊：
先切固定數量的碼位，超過上限就對半再切。所有分片都從完成的主字型切出，`layout_features=['*']`（保留 `calt`），
不帶 hinting（hinted 的框線在 headless Chromium 會讓格線接不起來）。分片內的 cmap 只留該群組的碼位，保證群組互斥。

`tests/check-web-zip.py out/JimMonoTC-<版本>-web.zip --masters dist` 檢查組好的 zip：檔名與群組、大小上限、群組互斥且聯集等於主字型 cmap、
`cjk-<N>` 在 Regular / Bold（以及 Italic / Bold Italic）相同、`latin` 有 `calt`、CSS 每個檔案一條 `@font-face`（family、weight、style、
`font-display: swap`、`unicode-range` 與檔案 cmap 一致）、授權檔齊全。

## CI 與發佈

`.github/workflows/build.yml`：

* push 到 `master`：四個樣式平行建構（`--split-web`）並各自跑 `verify.py`，成品一律以 workflow artifact 保留 30 天，
  不論是否發佈，都能在 workflow run 頁面下載（`JimMonoTC-<版本或 dev-sha>`：`-otf.zip`、`-web.zip`、`SHA256SUMS.txt`）。
  每個樣式的 job 即使 verify 失敗也會上傳 `dist-<Style>`，方便檢查。
  `font-patcher` 以乾淨的 Python 環境執行（不帶 `LD_LIBRARY_PATH` 等），避免 `actions/setup-python` 的
  libpython 蓋掉 FontForge 內嵌的系統版而載入失敗。
* push tag `v*`：同上，成功後建立 GitHub Release，附上兩個 zip 與 `SHA256SUMS.txt`，release notes 自動產生。
  tag 必須是 `v1.2.3` 或 `v1.2.3-rc1`（後者標為 pre-release），否則 workflow 失敗；`1.2.3` 會寫入字型的版本號。
  master 的一般建構版本號為 `0.0.0`。

```sh
git tag v0.3.0 && git push origin v0.3.0
```

## 驗證

`scripts/verify.py dist/JimMonoTC-Regular.otf`（WOFF2 分片用 `--partial`，可加 `--max-bytes 65536` 檢查大小）（`build.sh` 最後會自動執行）：

* 所有 glyph advance 只可能是 `0`、`W`、`2W`；East Asian Wide/Fullwidth 碼位必為 `2W`，其餘為 `W`
* CJK outline 不超出 `2W` cell
* `tests/width-cases.txt`：`A`=1、`中`=2、`中文`=4、`=>`=2、`!=`=2、`===`=3、Nerd icon=1 cell 等，
  分別在 calt 開 / 關時以 HarfBuzz shaping 量總 advance
* `tests/shaping.txt`：ligature 確實被替換（glyph 序列）且總 advance 不變
* 框線（`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`）的外框碰到它所連接的 cell 邊緣（左 x ≤ 0、右 x ≥ W、下 y ≤ hhea descender、上 y ≥ hhea ascender），
  相鄰 cell 才接得起來；只檢查直立樣式（斜體被傾斜）與完整字型，`--partial` 不檢查
* `calt` 可由 `DFLT`、`latn` script 觸達；name table 不含 Hack / Noto / Bitstream / Vera / Nerd
* 授權：`scripts/audit-licenses.py`（`build.sh` 建構前執行）逐項檢查 Nerd Fonts 的 14 組 glyph set 都有授權條目、授權檔案存在；
  patcher 升級後若多出未清點的 glyph set 會直接失敗。結果與尚待確認的問題見 [NOTICE.md](../NOTICE.md)；
  name table 也不得含 Reserved Font Name（Font Awesome、Pomicons、Weather Icons 等）
* 樣式一致：`usWeightClass`、`fsSelection`（bold / italic / regular 位元）、`macStyle`、`post.italicAngle` 與 name ID 2 相符

手動看瀏覽器渲染：建構後開 `tests/preview.html`（粉紅直條 = 每個 cell）。

## 已知限制與後續

* **Hinting**：CFF 版沒有 TrueType 指令（Noto 的 CFF hint 與新增的 ligature / CJK glyph 本來就不帶）。
  macOS 與高 DPI 螢幕不受影響；Windows 低 DPI 的小字級（約 9–14 px）可能較不銳利。
  需要 Hack 的 TrueType hinting 時用 `--format ttf`（且 CJK 為二次曲線近似）。
* CFF 未做 subroutinize，OTF 約 14 MB（見 `finalize.py --subroutinize`）。
* 完整 CJK 單一字型即可容納（54,757 glyph），所以桌面端不需拆成多個字型；拆分只用於網頁分片。
  每個樣式都是各自獨立的字型檔，各自享有 65,535 的 glyph 上限。
* Italic / Bold Italic 的 CJK 是合成斜體（機械式剪切），不是設計過的斜體。
* `::` `//` `||` `??` `/*` `*/` 是「縮小字元間距」的連字（直接複製 Hack 該樣式的字形，曲線與斜體都原樣保留），
  `>>` `<<` `>>>` `<<<` 是互相套疊的 chevron，`|>` `<|` 是直條加 chevron。Italic 的 `|` 是 Hack 本身斷開的設計，`||` `|>` 沿用。
* `>=` `<=` 以橫向拉寬的 chevron 加底線繪成（近似 ≥ ≤），不是 Fira Code 的設計；斜體時連字仍直立。
* 尚未做：
  * 在實際 terminal（Windows Terminal、WezTerm、Kitty…）與 Firefox 上的實機測試
  * 其他連字（例如 `&&`：Hack 的 `&` 字面幾乎撐滿格子，縮距沒有意義，所以不做；`++` `--` `..` 等同理，收益不明顯）
  * [NOTICE.md](../NOTICE.md)「Open points」中需要人工判斷的授權問題（如 Font Awesome 的 CC BY 4.0 / OFL 取捨）
