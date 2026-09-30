# Jim Mono TC

給程式碼與 terminal 用的等寬字型，**中文字剛好是英文字母的兩倍寬**，對齊不會跑掉。

* **Latin**：[Hack](https://github.com/source-foundry/Hack)，清楚好讀的程式字型
* **中文（繁體）**：[Noto Sans CJK TC](https://github.com/notofonts/noto-cjk)，含常用字、次常用字、假名、注音與全形標點
* **圖示**：[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) 的 Powerline、Font Awesome、Devicons 等，每個佔一格
* **連字（ligatures）**：`==` `!=` `=>` `->` `>=` `::` `|>` 等 29 種
* **四種樣式**：Regular、Bold、Italic、Bold Italic
* 同一份字型可用在本機（`.otf`）與網頁（`.woff2`）

```text
abcdefghij      ← 每個英文字母 1 格
中文字元對齊     ← 每個中文字 2 格
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

解壓縮 `-otf.zip` 後，四個 `.otf` 一起安裝（每個約 14 MB，因為內含完整中文）：

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
| `latin` | 基本拉丁、常用標點（含連字） | 約 19 KB |
| `latin-ext` | 拉丁擴充、組合符號、一般標點 | 約 19 KB |
| `greek-cyrillic` | 希臘、西里爾等 | 約 31 KB |
| `box` | 框線與方塊（U+2500–259F） | 約 3 KB |
| `symbols` | 箭頭、數學與雜項符號 | 約 28 KB |
| `cjk-<N>` | 中文（雙格寬字元），`N` 是 Noto Sans TC 在 Google Fonts 的頻率分片編號 | 1.8–48 KB，共 93 個 |
| `cjk-x<N>` | 其餘中文（罕用字、擴充區） | 15–63 KB，共約 125 個 |
| `icons-<N>` | Nerd Fonts 圖示（私用區） | 25–63 KB，共 43 個 |

只需要中英文與框線的網站，取 `latin`、`latin-ext`、`greek-cyrillic`、`box`、`symbols` 與 `cjk-<N>` 即可，
不用的群組（常見的是 `icons-*` 與 `cjk-x*`）直接刪掉，並同步刪除 `JimMonoTC.css` 中對應的 `@font-face`。
自行託管時可用 `--url-prefix` 之外的方式改路徑：CSS 內的網址都是 `/fonts/<檔名>`。

> 從 0.1.0 升級：舊的 `latin`、`icons`、`cjk-common`、`cjk-big5`、`cjk-<N>`（依數量切的）檔名都已不存在，
> 請改用上表的群組並更新網址。

## 連字

| 類別 | 連字 |
| --- | --- |
| 比較 | `==` `===` `!=` `!==` `>=` `<=` `=/=` |
| 箭頭 | `->` `<-` `=>` `-->` `<--` `==>` `<==` `<->` `<=>` `<==>` |
| 其他 | `::` `//` `\|\|` `??` `/*` `*/` `>>` `<<` `>>>` `<<<` `\|>` `<\|` |

連字與原本的字元同寬，所以 terminal 逐格繪製也不會錯位。不想要連字時關閉軟體的 ligature 選項即可。

## 已知限制

* **Italic 的中文是合成斜體**：Noto Sans CJK 沒有斜體，Italic 與 Bold Italic 的中文是把 Regular / Bold 依 Hack 的斜角（11°）傾斜而成，英文則是 Hack 原本設計的斜體。
* **小字級**：字型沒有 TrueType hinting。Windows 低解析度螢幕上約 9–14 px 的小字可能較不銳利；macOS 與高解析度螢幕不受影響。
* **檔案較大**：每個樣式約 14 MB，因為包含完整中文字集。
* **`>=` `<=`** 是自行繪製的近似 ≥ ≤，不是其他字型的設計。

## 授權

字型本身以 [SIL Open Font License 1.1](LICENSE) 授權，可自由使用、散布與修改，唯一限制是不能單獨販售，
且修改版不得使用保留字型名。

字型合併了多個上游專案，各自的歸屬與授權在 [NOTICE.md](NOTICE.md)，授權文字放在 `licenses/`
（release 的兩個 zip 都附上）。

## 想自己建構或修改？

見 [docs/BUILDING.md](docs/BUILDING.md)：建構步驟、pipeline 說明、CI 與發佈流程、驗證項目。
