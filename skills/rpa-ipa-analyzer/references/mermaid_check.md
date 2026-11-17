# Mermaid 图表硬约束与校验

> 报告里的图不是装饰，**渲染失败就等于没有图**。本文件是 `SKILL.md`「Mermaid 铁律」的细则，
> 由 `references/mermaid_check.md` 引用、由 `scripts/_extract/mermaid.py` 自动检查。

---

## 1. 一次真实事故（2026-10-27）

报告第一张图写成（**下面是错误示范，用 text 围栏以免被当成真图**）：

```text
flowchart TB
  Main["主流程"]
  Main -->|int(total) != 0| Borrow["处理证件借用数据"]
```

mermaid 11.17.2 报：

```
Parse error on line 6:
...Main -->|int(total) != 0| Borrow
--------------------^
Expecting ... got 'PS'
```

`PS` = 左括号 token。**边标签里的 `(` 会被解析器当成形状起始符**，整张图不渲染；
markdown 其余部分正常，所以只看文本时完全发现不了。

**根因**：把代码条件原样搬进边标签。副作用：`), }`、`;` 同理。

**结论**：边标签是「纯文本」，不是表达式、不是代码。条件要么去掉括号（`total!=0`），
要么把判断挪到节点标签里（`IF2{"total!=0?"}`，括号放在引号内是安全的）。

## 1.2 第二起事故（同一天，3.3.3 补漏）

3.3.2 的检查器只查**边标签**，于是同一技能的下一份报告又栽在**节点标签**上：

```text
flowchart TB
  G1[查找JSON → 数据合并(三分组去重) → EXCEL美化(3 sheet+判断点公式)]
```

mermaid 12.2.0 报 `Parse error on line 15 ... expecting ..., got 'PS'`；
同时该图还有一条 `M2 -.try.-> G1`（虚线边带文字但少了空格）也不合法。

- 节点标签 `[...]` / `{...}` / `(...)` 的**内容**和边标签一样是「标签文本」，
  未加引号时 `( ) [ ] { } | ;` 全部是语法字符。
- 正确写法只有一种：**整体加双引号** —— `G1["查找JSON → 数据合并(三分组去重) → …"]`。
- 3.3.3 起：新增 **E10**（未加引号的节点/子图标签含禁用字符）、**E11**（`-.文字.->`）、
  **W7**（未加引号的节点标签，按铁律应统一加引号），并加 `--self-test` 把两起事故的写法锁进回归用例。

---

## 2. 硬规则（ERROR，必须为 0）

| 编号 | 规则 | 反例 → 正例 |
|------|------|-------------|
| E1 | 首行必须是受支持图类型 | `flow chart` → `flowchart`（写成 `flowchart TB` 最稳） |
| E2 | 边标签禁止 `( ) [ ] { } ;` | `-->|int(total) != 0|` → `-->|total!=0|` |
| E3 | （已降级为 W6）边标签含 `"` | 见 W6 |
| E4 | 每行 `\|` 必须成对 | `A -->|是 B` → `A -->|是| B` |
| E5 | 引号内标签禁止 `\|` | `["a|b"]` → `["a / b"]` |
| E6 | 每行 `"` 数量必须是偶数 | `["未闭合` → `["未闭合"]` |
| E7 | `subgraph` 必须 `end` 关闭 | — |
| E8 | 代码围栏必须闭合、块不能为空 | — |
| E9 | 不用制表符缩进 | `\t` → 两个空格 |
| **E10** | **节点/子图标签未加引号且含 `( ) [ ] { } \| ;`** | `G1[合并(去重)]` → `G1["合并(去重)"]` |
| **E11** | **虚线边带文字写成 `-.文字.->`** | `B -.碳送.-> S` → `B -. 碳送 .-> S` 或 `B -.->\|碳送\| S` |

> E3 原为「边标签含双引号」，2026-10-27 全工作区扫描发现 10 处历史报告用了 `-->|"…"|`
> （mermaid ≥10 合法），为避免误报已降级为 W6。当前 ERROR 共 10 条：E1/E2/E4/E5/E6/E7/E8/E9/E10/E11。

## 3. 可读性规则（WARN，建议清零）

单图节点数、方向决定渲染尺寸，**尺寸决定字还能不能看**：

| 编号 | 触发 | 后果 | 处置 |
|------|------|------|------|
| W1 | 单图节点 > 20 | 布局拥挤、交叉线多 | 拆成 2 张（调用链 / 数据流） |
| W2 | `flowchart LR` 且节点 > 12 | 实测宽度可到 3000px，缩到页宽后字约 4px | 改 `TB`，或拆图 |
| W3 | `stateDiagram` 裸中文状态 ID | 旧渲染器可能不认 | `state "未处理" as s0` 再引用 `s0` |
| W4 | 标签含 `#` / 裸 HTML | 实体转义差异 | 用中文或 `<br/>` |
| W5 | 标签含字面量 `\n` | 不换行 | 用 `<br/>` |
| W6 | 边标签含 `"` | 仅 mermaid ≥10 支持（原 E3 降级） | 去掉引号，如 `-->|是|` |
| **W7** | **节点标签未加引号（含中文/空格/箭头）** | 按铁律应统一加引号；老报告会有 | 改 `A["开始"]`（本项按图聚合为 1 条，不刷屏） |

**经验尺寸**（1500px 视口实测，越接近页宽越好）：

| 图 | 尺寸 | 评价 |
|----|------|------|
| 主链 13 节点 TB | 960 × 3428 | 宽度好、纵向长，可滚动，可接受 |
| 6 个调用方 + 1 汇聚 LR | 1316 × 1180 | 好 |
| 精简数据流 10 节点 TB | 1168 × 1162 | 好 |
| 页面流程 8 节点 TB | 700 × 1852 | 好 |
| 22 节点数据流 LR | 2948 × 1138 | **差**：缩放后看不清 → 精简为 10 节点 |

> 目标：**宽度 ≤ ~1300px**；宁可长（纵向滚动），不要宽（缩放后字太小）。

---

## 4. 定稿前必跑（30 秒）

```powershell
$SK = "<SK>"
& "$SK\scripts\rpa.cmd" check-mermaid --self-test     # 检查器自检：12 例，两起事故的写法必须被抓到
& "$SK\scripts\rpa.cmd" check-mermaid "<project>\分析报告_xxx.md"
#   通过 → exit 0，打印「[check-mermaid] 通过」
#   失败 → exit 2，逐条打印 ERROR（含文件:行号）
& "$SK\scripts\rpa.cmd" check-mermaid "<project>" --strict   # 连 WARN 一起清零
```

也可直接对目录跑（递归 `*.md` / `*.mmd`）：

```powershell
& "$SK\scripts\rpa.cmd" check-mermaid "导入应用XXXX" --strict
```

规则实现见 `scripts/_extract/mermaid.py`（纯标准库，Python 3.8 可用，不联网）。

---

## 5. 可选：真渲染校验（静态检查通过后再做，图表多时值得）

静态检查只能挡住「已知会报错」的写法；**想 100% 确认渲染，就用报告的实际渲染器跑一遍**。

1. 先确认渲染器版本（决定语法上限）。DSH 桌面端：

```powershell
Select-String "$env:USERPROFILE\.dsh\profiles\desktop\pnpm-lock.yaml" -Pattern 'mermaid@'
#   如 mermaid@11.17.2 → 按这个版本校验
```

2. 临时装同版本 + 无头浏览器（用系统已装 Chrome，不下载 Chromium）：

```powershell
$d="$env:TEMP\mmcheck"; New-Item -ItemType Directory -Force $d | Out-Null; cd $d
npm init -y | Out-Null
npm i mermaid@11.17.2 puppeteer-core --silent
```

3. 用下面的脚本 `render.mjs` 跑：从 md 里抽 ```mermaid 块 → 注入浏览器 → `mermaid.render()`，
任一失败即退出码 2（脚本可直接放在 `$d` 下重复用）：

```js
// render.mjs  node render.mjs <report.md>
import fs from 'node:fs'; import path from 'node:path'; import puppeteer from 'puppeteer-core';
const CHROME='C:/Program Files/Google/Chrome/Application/chrome.exe';
const md=fs.readFileSync(process.argv[2],'utf8');
const blocks=[...md.matchAll(/```mermaid\r?\n([\s\S]*?)```/g)].map(m=>m[1]);
const umd=fs.readFileSync(path.resolve('node_modules/mermaid/dist/mermaid.min.js'),'utf8');
const b=await puppeteer.launch({executablePath:CHROME,headless:true,args:['--no-sandbox']});
const p=await b.newPage(); await p.setContent('<body></body>'); await p.addScriptTag({content:umd});
let bad=0;
for(let i=0;i<blocks.length;i++){
  const r=await p.evaluate(async(c,id)=>{try{window.mermaid.initialize({startOnLoad:false,securityLevel:'loose'});
    return {ok:true,n:(await window.mermaid.render(id,c)).svg.length};}catch(e){return {ok:false,m:String(e.message||e)};}},blocks[i],'d'+i);
  console.log(`#${i+1}`, r.ok?`RENDER OK ${r.n}B`:`RENDER FAIL ${r.m.split('\n')[0]}`); if(!r.ok)bad++;
}
await b.close(); process.exit(bad?2:0);
```

> 用 `addScriptTag({content})` 注入 UMD；直接 `<script src="file://...">` 在部分环境下不会挂载
> `window.mermaid`，会误报「Cannot read properties of undefined (reading 'initialize')」。

4. 需要肉眼确认版式时，把 render 出的 `svg` 塞进 `#host` 再 `elementHandle.screenshot()`
   即可得到 PNG（1500×1100、`deviceScaleFactor:2` 足够看清）。

---

## 6. 交付检查清单（analyze / update / audit 通用）

- [ ] `check-mermaid` exit 0（`--strict` 时 WARN 也 0）；提交前跑过一次 `--self-test`
- [ ] 边标签无括号；**节点/子图标签全部带双引号**（E10/W7 清零）；虚线边用 `-. 文字 .->`
- [ ] 每张图都有小标题（`**图 N：xxx**`），正文有对应文字说明，图不是唯一信息载体
- [ ] 单图宽度 ≤ ~1300px（或用 `TB`）
- [ ] 图里出现的文件名 / 节点名与正文一致（同一实体只能一种叫法）
- [ ] 至少跑过一次实际渲染（图表 ≥3 张或客户明确要看图时）
