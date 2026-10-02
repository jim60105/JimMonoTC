# 開發與建構指南

給想自己建構、修改或除錯 Jim Mono TC 的人。一般使用請看 [README](../README.md)。

## 建構

需要 Python 3.10+（套件見 `requirements.txt`，含 `unicodedata2`、`skia-pathops`）、`curl`、`unzip`、`git`。
不再需要 FontForge。
`hb-shape`（HarfBuzz CLI）可選，有安裝時 `verify.py` 會額外用它交叉驗證。

```sh
python3 -m pip install -r requirements.txt
scripts/build.sh                 # -> dist/JimMonoTC-{Regular,Bold,Italic,BoldItalic}.{otf,woff2}, JimMonoTC.css
scripts/build.sh --split-web     # WOFF2 依 unicode-range 分片（見「網頁使用」）
scripts/build.sh --format ttf    # 改輸出 TrueType（二次曲線；Cascadia 的 hinting 保留在 Latin）
```

選項：

* `--styles "Regular Bold"`：只建構部分樣式，預設四種全建。
* `--format otf|ttf`：預設 `otf`（CFF）。Noto 的三次曲線原樣搬入、Cascadia 的二次曲線
  精確升階為三次，沒有任何曲線被近似。`ttf` 則把 Noto 以 Cu2Qu 近似成二次曲線。
* `--charset all|big5-common|big5|FILE`：要併入的 CJK 字集。預設 `all`（Noto 有的全部 wide 碼位，
  約 43,000 個碼位、42,779 個 glyph，整個字型約 57,500 個 glyph，低於 65,535 的上限）；
  `big5-common`（約 5,900 碼位）、`big5`（約 13,500 碼位）可縮小成品；`FILE` 為純文字檔
  （字元或 `U+XXXX[-YYYY]`）。假名、注音、全形標點一律會併入。
* `--cjk-scale N`：CJK 字面相對 em 的大小，預設 `1.0`（字面完全落在 Cascadia 的
  ascent / descent 內）。想讓漢字看起來更飽滿可試 `1.1`，但注意上下緣可能超出行高。

首次執行會下載並以 SHA-256 驗證固定版本的輸入（`sources/versions.env`、
`sources/checksums.sha256`）到 `.cache/`；Noto 每個檔案約 16 MB（Regular、Bold、Black 三個）。
GitHub 直接下載 Noto 失敗時會改用 sparse git checkout。完整 CJK 的單一樣式約 2 分鐘（CJK 合併約 1 分鐘），
`--split-web` 約 270 個切片，每個樣式再多約 3 分鐘。

### Pipeline

```text
Cascadia Code NF ─► prepare-base.py ─► add-arrows.py ─► merge-cjk.py ─► finalize.py ─► verify.py
                                                                         └─► build-web.py (WOFF2 subset)
```

* 輸入是 Cascadia Code release 內的 static `CascadiaCodeNF-{Regular,Bold,Italic,BoldItalic}.ttf`：
  Latin、連字（`calt`，每個來源字元仍是一個 `W` 寬的 glyph，前面的 cell 是空的 `LIG`，箭頭是
  `*_start.seq` / `*_middle.seq` / `*_end.seq` 串接）、Powerline 與 Nerd Font 圖示都直接沿用。
* `prepare-base.py`：
  * Cascadia 的方塊元素、Legacy Computing（含 Supplement）與 Powerline 分隔符號是依 Windows metrics
    （usWinDescent..usWinAscent = −480..2226）畫的，比行高（hhea / typo −480..1900）高。
    這些 glyph 垂直縮放到剛好填滿一行；框線本來就置中於行內、只是超出去接合，不動。
  * Cascadia NF 內建的是較舊的 Nerd Fonts，缺少約 1,190 個圖示（新的 devicons、Font Awesome、codicons、
    font-logos 等）。這些從 Nerd Fonts 3.4.0 FontPatcher 封存檔的 glyph 原始字型補上，碼位對應讀自
    `font-patcher` 的 glyph-set 表（`scripts/nerd_sets.py`），縮放用 Cascadia 自己的規則
    （cascadia-code `sources/nerdfonts/full/process.py`：寬度貼齊 cell 扣 side bearing 或高度貼齊 cap height，
    兩方向置中）。用 Cascadia 已有的圖示驗證過：這個移植對大部分 glyph set 的誤差中位數約 0.2 unit，
    font-patcher 的縮放則固定差約 20 unit，所以不跑 font-patcher。
  * 進度條（U+EE00–EE0B，Nerd Fonts 的 `extraglyphs.sfd`）依 font-patcher 的放法（scale group、overlap）放進 cell，
    相鄰片段才接得起來。
* `add-arrows.py`：Cascadia 只有基本箭頭。箭頭區塊中 Cascadia 沒有、Noto Sans CJK 有的（約 23 個）取自
  Noto **Black**：等比縮進 Cascadia 箭頭的框（`→` 的寬、`↕` 的高），以 `→` 的軸線置中，
  再用 skia-pathops 外擴輪廓到和該樣式 `→` 的箭桿一樣粗（Bold 會更粗），Italic 依斜角傾斜。
  這些箭頭是 East Asian Ambiguous / Neutral，所以是單格。
* `merge-cjk.py`：只補 Cascadia 沒有的全形字元，縮放到同一 UPM、置中於 `2W`（Italic 依 Cascadia 的 `italicAngle` 以行中線為軸斜切，
  少數撐滿格子的字元，如 U+FFE3，斜切後會平移回格內）；`otf` 時整個字型
  改寫成 CFF（外框方向一併反轉為 CFF 的逆時針）。另外取消對應 emoji 寬度碼位的單 cell glyph
  （U+25FD、U+25FE、U+26A1、U+2B1B、U+2B1C），但 U+2630 ☰ 保留單格。
  East Asian Width 一律用 `unicodedata2`（目前的 Unicode），不用 Python 內建的舊表：
  例如 Python 3.11 的 Unicode 14 會把 Unicode 16 新增的 Legacy Computing Supplement 誤判為全形。
* `finalize.py`：新 family name（含 CFF 內部名稱；Cascadia 的 Reserved Font Name 與 Microsoft 的商標、授權 name record 都換掉）、
  依樣式設定 `usWeightClass` / `fsSelection` / `macStyle`、`OS/2.xAvgCharWidth = W`、monospaced panose、
  Windows metrics 設成和行高一致、清掉過時表。
  `--subroutinize` 可用 compreffor 壓縮 CFF charstring，但 5 萬多 glyph 時極慢（本機超過 40 分鐘 CPU 仍未完成），預設關閉。
* `build-web.py`：一律由完成的主字型（OTF / TTF）產生 WOFF2，保證 metrics 與 feature 一致（見下節「網頁分片」）。

### 網頁分片

`build-web.py --split`（`build.sh --split-web`）把 cmap 切成互斥、合起來涵蓋整個 cmap（扣掉 U+0000、U+000D、U+FEFF）的群組。
群組名稱是對外介面（下游專案依名稱挑選），不要改名：

* `latin`、`latin-ext`、`greek-cyrillic`、`arabic-hebrew`、`box`、`symbols`：單格寬、非私用區的碼位，依 `build-web.py` 內 `WINDOWS` 的順序先到先得。
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
* push tag `v*`：同上，成功後建立 GitHub Release，附上兩個 zip 與 `SHA256SUMS.txt`，release notes 自動產生。
  tag 必須是 `v1.2.3` 或 `v1.2.3-rc1`（後者標為 pre-release），否則 workflow 失敗；`1.2.3` 會寫入字型的版本號。
  master 的一般建構版本號為 `0.0.0`。

```sh
git tag v0.4.0 && git push origin v0.4.0
```

## 驗證

`scripts/verify.py dist/JimMonoTC-Regular.otf`（WOFF2 分片用 `--partial`，可加 `--max-bytes 65536` 檢查大小）（`build.sh` 最後會自動執行）：

* 所有 glyph advance 只可能是 `0`、`W`、`2W`；East Asian Wide/Fullwidth 碼位（依 `unicodedata2`）必為 `2W`（U+2630 例外，刻意保留單格），其餘為 `W`
* CJK outline 不超出 `2W` cell
* `tests/width-cases.txt`：`A`=1、`中`=2、`中文`=4、`=>`=2、`!=`=2、`===`=3、Nerd icon、補上的箭頭、方塊元素=1 cell 等，
  分別在 calt 開 / 關時以 HarfBuzz shaping 量總 advance
* `tests/shaping.txt`：Cascadia 的連字確實被替換（glyph 序列，`*.liga` + `LIG`、箭頭為 `*.seq`）且總 advance 不變
* 框線（`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`）的外框碰到它所連接的 cell 邊緣（左 x ≤ 0、右 x ≥ W、下 y ≤ hhea descender、上 y ≥ hhea ascender），
  相鄰 cell 才接得起來；方塊元素（`█ ▌ ▐ ░ ▒ ▓`）、Powerline 分隔符號與 Legacy Computing 的全高 glyph 必須剛好從 hhea descender 到 ascender
  （確認 `prepare-base.py` 縮放過）。四種樣式都檢查（Cascadia 的斜體框線是直立的），`--partial` 不檢查
* `calt` 可由 `DFLT`、`latn` script 觸達；name table 不含 Cascadia / Caskaydia / Microsoft / Noto / Nerd 等上游名稱
* 授權：`scripts/audit-licenses.py`（`build.sh` 建構前執行）逐項檢查 Nerd Fonts 的 14 組 glyph set（Cascadia 內建的加上補上的）都有授權條目、授權檔案存在；
  patcher 升級後若多出未清點的 glyph set 會直接失敗。結果與尚待確認的問題見 [NOTICE.md](../NOTICE.md)；
  name table 也不得含 Reserved Font Name（Cascadia Code、Font Awesome、Pomicons、Weather Icons 等）
* 樣式一致：`usWeightClass`、`fsSelection`（bold / italic / regular 位元）、`macStyle`、`post.italicAngle` 與 name ID 2 相符

手動看瀏覽器渲染：建構後開 `tests/preview.html`（粉紅直條 = 每個 cell）。

## 已知限制與後續

* **Hinting**：CFF 版沒有 TrueType 指令（Noto 的 CFF hint 與新增的 CJK glyph 本來就不帶）。
  macOS 與高 DPI 螢幕不受影響；Windows 低 DPI 的小字級（約 9–14 px）可能較不銳利。
  需要 Cascadia 的 TrueType hinting 時用 `--format ttf`（且 CJK 為二次曲線近似；被縮放或新增的 glyph 不帶 hint）。
* CFF 未做 subroutinize，OTF 約 15 MB（見 `finalize.py --subroutinize`）。
* 完整 CJK 單一字型即可容納（約 57,500 glyph），所以桌面端不需拆成多個字型；拆分只用於網頁分片。
  每個樣式都是各自獨立的字型檔，各自享有 65,535 的 glyph 上限。
* Italic / Bold Italic 的 CJK 是合成斜體（機械式剪切），不是設計過的斜體。
* 補上的箭頭保留 Noto 的造型，只調整大小與粗細；Noto 也沒有的箭頭（Supplemental Arrows 大部分）交給系統字型。
* Cascadia 的 Italic 沒有阿拉伯文、希伯來文，所以 Italic / Bold Italic 沒有 `arabic-hebrew` 網頁群組。
* 行高沿用 Cascadia 的 hhea / typo（−480..1900，約 1.16 em），Windows metrics 也設成相同值；
  Cascadia 原版在 Windows GDI 程式中行高較大（usWinAscent 2226），本字型則各平台一致。
* 尚未做：
  * 在實際 terminal（Windows Terminal、WezTerm、Kitty…）與 Firefox 上的實機測試
  * [NOTICE.md](../NOTICE.md)「Open points」中需要人工判斷的授權問題（如 Font Awesome 的 CC BY 4.0 / OFL 取捨）
