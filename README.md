# Jim Mono TC

融合等寬字型，**中文調整為英數的兩倍寬**，對齊再也不會跑掉！

## 食譜

* **Latin**：[Cascadia Code](https://github.com/microsoft/cascadia-code)，Microsoft 為 Windows Terminal 設計的程式字型，
  也涵蓋希臘、西里爾、阿拉伯、希伯來文、框線、方塊元素與 Legacy Computing 符號
* **中文（繁體）**：[Noto Sans CJK TC](https://github.com/notofonts/noto-cjk)，含常用字、次常用字、假名、注音與全形標點
* **圖示**：Cascadia Code 內建的 Powerline 與 [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) 圖示，
  並補齊到 Nerd Fonts 3.4.0 的完整集合（約 1 萬個），每個佔一格、大小風格一致
* **連字（ligatures）**：Cascadia Code 的整套連字，包括 `->` `=>` `<==>` `|->` 等箭頭與 `!=` `::` `&&` `</>` 等
* **箭頭**：Cascadia 沒有的 Unicode 箭頭（`↖` `⇒` `⇄` `⤴` `⬅` 等）取自 Noto Sans CJK，調整成單格並對齊 Cascadia 箭頭的線條粗細
* **四種樣式**：Regular、Bold、Italic（Cascadia 的真斜體）、Bold Italic
* 同一份字型可用在本機（`.otf`）與網頁（`.woff2`）

```text
012abcdefghi     ← 每個英數 1 格
中文字元對齊     ← 每個中文 2 格
```

## 下載

到 [Releases](https://github.com/jim60105/JimMonoTC/releases) 下載：

| 檔案 | 用途 |
| --- | --- |
| `JimMonoTC-<版本>-otf.zip` | 安裝到電腦（Regular、Bold、Italic、Bold Italic 各一個 `.otf`） |
| `JimMonoTC-<版本>-web.zip` | 放到網站（`.woff2` 分片與 `JimMonoTC.css`） |
| `SHA256SUMS.txt` | 檔案雜湊值，用來核對下載是否完整 |

每次 push 到 `master` 也會建構一份，可在 [Actions](https://github.com/jim60105/JimMonoTC/actions)
頁面的 workflow run 下載 artifact（開發版，版本號為 `0.0.0`）。

## 安裝與使用

### 安裝字型

解壓縮 `-otf.zip` 後，四個 `.otf` 一起安裝（每個約 15 MB，因為內含完整中文）：

* **Windows**：全選檔案 → 右鍵 → 為所有使用者安裝
* **macOS**：雙擊檔案 → 安裝字體
* **Linux**：複製到 `~/.local/share/fonts/`，再執行 `fc-cache -f`

安裝後字型名稱是 **`Jim Mono TC`**。

### Terminal / 編輯器

把字型設為 `Jim Mono TC` 即可。範例：

```jsonc
// VS Code settings.json
"editor.fontFamily": "'Jim Mono TC', monospace",
"editor.fontLigatures": true
```

```lua
-- WezTerm
config.font = wezterm.font("Jim Mono TC")
```

```toml
# Alacritty
[font.normal]
family = "Jim Mono TC"
```

Windows Terminal 在設定 → 外觀 → 字型 選擇 `Jim Mono TC`。

**連字**需要支援 OpenType 的軟體才會顯示（WezTerm、Kitty、Windows Terminal、VS Code 等）。
不支援時字元寬度依然正確，只是會顯示成原本的分開字元。
**Emoji** 不含在字型內，會由系統字型補上。

### 網頁

解壓縮 `-web.zip`，把 `.woff2` 與 `JimMonoTC.css` 放到網站的 `/fonts/`（CSS 內的路徑預設是 `/fonts/`）：

```html
<link rel="stylesheet" href="/fonts/JimMonoTC.css">
```

```css
pre, code {
  font-family: "Jim Mono TC", monospace;
  font-variant-ligatures: contextual;  /* 顯示連字 */
}
```

字型已依 `unicode-range` 切成多個小檔（每個 `.woff2` 都不超過 64 KiB），瀏覽器只會下載頁面實際用到的部分，
不需要一次載入完整字型。四種樣式共用同一個 family 名稱，用 `font-weight`、`font-style` 切換。

每個樣式的檔案名稱是 `JimMonoTC-<樣式>.<群組>.woff2`，群組如下（名稱固定，可以依名稱挑選）：

| 群組 | 內容 | 大小（Regular） |
| --- | --- | --- |
| `latin` | 基本拉丁、常用標點（含連字） | 約 27 KB |
| `latin-ext` | 拉丁擴充、組合符號、一般標點 | 約 23 KB |
| `greek-cyrillic` | 希臘、西里爾等 | 約 15 KB |
| `arabic-hebrew` | 阿拉伯文、希伯來文（Italic 樣式沒有這個群組） | 約 49 KB |
| `box` | 框線、方塊元素與 Legacy Computing 符號 | 約 18 KB |
| `symbols` | 箭頭、數學與雜項符號 | 約 17 KB |
| `cjk-<N>` | 中文（雙格寬字元），`N` 是 Noto Sans TC 在 Google Fonts 的頻率分片編號 | 1.8–48 KB，共 93 個 |
| `cjk-x<N>` | 其餘中文（罕用字、擴充區） | 15–63 KB，共約 125 個 |
| `icons-<N>` | Nerd Fonts 圖示（私用區） | 23–64 KB，共 44 個 |

只需要中英文與框線的網站，取 `latin`、`latin-ext`、`greek-cyrillic`、`box`、`symbols` 與 `cjk-<N>` 即可，
不用的群組（常見的是 `arabic-hebrew`、`icons-*` 與 `cjk-x*`）直接刪掉，並同步刪除 `JimMonoTC.css` 中對應的 `@font-face`。
自行託管時可用 `--url-prefix` 之外的方式改路徑：CSS 內的網址都是 `/fonts/<檔名>`。

## 連字

使用 Cascadia Code 的整套連字，例如：

| 類別 | 連字 |
| --- | --- |
| 箭頭 | `->` `<-` `=>` `-->` `<--` `==>` `<==` `<->` `<=>` `<==>` `\|->` `<-\|` `\|=>` `->>` `<<-` `=>>` |
| 比較 | `==` `===` `!=` `!==` `>=` `<=` `<>` |
| 其他 | `::` `:::` `:=` `//` `///` `/*` `*/` `&&` `\|\|` `??` `?.` `..` `...` `\|>` `<\|` `</` `/>` `</>` `<!--` `++` `**` `>>=` `www` 等 |

連字與原本的字元同寬，所以 terminal 逐格繪製也不會錯位。不想要連字時關閉軟體的 ligature 選項即可。
Cascadia 的 stylistic set 也都保留，例如 `ss19`（斜線零）、`ss20`（控制字元圖示），Italic 另有 `ss01`（草寫體）。

## 已知限制

* **Italic 的中文是合成斜體**：Noto Sans CJK 沒有斜體，Italic 與 Bold Italic 的中文是把 Regular / Bold 依 Cascadia 的斜角（10°）傾斜而成，英文則是 Cascadia 原本設計的斜體。
* **補上的箭頭是改造過的 Noto 字形**：Noto 的箭頭原本是全形設計，縮成單格後加粗到和 Cascadia 的 `→` 一樣粗，造型仍是 Noto 的。Noto 也沒有的箭頭由系統字型顯示。
* **`☰`（U+2630）保持單格**：Unicode 16 把它改成雙格寬，但多數 terminal 仍當單格，Powerline / Nerd Fonts 也當單格圖示使用。
* **小字級**：OTF 沒有 TrueType hinting。Windows 低解析度螢幕上約 9–14 px 的小字可能較不銳利；macOS 與高解析度螢幕不受影響。
* **檔案較大**：每個樣式約 15 MB，因為包含完整中文字集。
* **Italic 沒有阿拉伯文、希伯來文**：Cascadia 的斜體本身就沒有這兩種文字。

## 授權

字型本身以 [SIL Open Font License 1.1](LICENSE) 授權，可自由使用、散布與修改，唯一限制是不能單獨販售，
且修改版不得使用保留字型名。

字型合併了多個上游專案，各自的歸屬與授權在 [NOTICE.md](NOTICE.md)，授權文字放在 `licenses/`
（release 的兩個 zip 都附上）。

## 想自己建構或修改？

見 [docs/BUILDING.md](docs/BUILDING.md)：建構步驟、pipeline 說明、CI 與發佈流程、驗證項目。
