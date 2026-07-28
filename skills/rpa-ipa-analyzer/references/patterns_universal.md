# Universal RPA Design Patterns

> 通用结构模式，跨项目和领域适用。在 Layer 2.3 中逐节点匹配。
> 匹配规则：全部 must_hit → [高置信度]；>=50% must_hit + >=1 optional → [中置信度]。
> 最大模式数量硬限制 <= 15。连续 10 次分析无命中 → deprecated。

---

## UP-01: 模板驱动Excel生成

**一句话描述**：打开 Resources/ 中的预格式化 Excel 模板，填充数据后另存为动态文件名。

**必须命中（AND）**：
- [ ] `openpyxl.load_workbook()` 或 `xlrd.open_workbook()` 的参数路径在 Resources/ 目录下
- [ ] 使用 `cell(row, col).value = ...` 或类似逐单元格写入
- [ ] `.save()` 的文件名包含动态变量（日期、参数值、时间戳）
- [ ] 存在对应的 `excel_open_or_create` 或 `excel_close` 组件

**可选信号（OR）**：
- [ ] Resources/ 目录中存在 .xlsx 或 .xls 模板文件
- [ ] 代码中有 `sheet = wb.active` 或 `wb.get_sheet_by_name()`

**报告输出**：节点分析中标注 `[通用模式: UP-01 模板驱动Excel生成 (置信度: 高/中)]`。在 §5.1 模式表中列出。在 §5.3 评价是否可简化模板路径配置。

---

## UP-02: 多源数据合并管道

**一句话描述**：从多个 Excel 文件或 Sheet 加载数据 → 顺序左连接富化 → 最终合并 → 导出。

**必须命中（AND）**：
- [ ] 代码中存在 >=3 个 `pd.read_excel()` 或 `pd.read_csv()` 调用
- [ ] 存在 `pd.merge()` 链（>=2 次调用），使用 `how='left'` 或 `how='outer'`
- [ ] 最终使用 `df.to_excel()` 输出

**可选信号（OR）**：
- [ ] 加载数据的变量名含 "df" 前缀
- [ ] 使用 `@dataclass` 或类似容器承载加载数据
- [ ] 存在中间 drop/rename 列操作

**报告输出**：节点分析中标注 `[通用模式: UP-02 多源数据合并管道]`。在 §5.1 列出。在 §5.3 评价是否可用 `pd.concat` 替代逐列 merge。

---

## UP-03: 双模操作（浏览器/API切换）

**一句话描述**：全局参数控制流程在浏览器自动化模式和 HTTP API 模式间切换。

**必须命中（AND）**：
- [ ] 存在 `process_if` 条件分支读取全局参数（mode / run_mode / browser_mode）
- [ ] 两个分支分别使用 `browser_inject_js_code` 和 `web_http_request`（或等效组件）
- [ ] 两种模式共享相同的数据输入（同一批 Excel 参数）

**可选信号（OR）**：
- [ ] 浏览器分支有 `mouse_single_click` / `keyboard_text_input` 链
- [ ] API 分支有 `Authorization: Bearer` 头
- [ ] 模式切换参数在 `globalParams.json` 中定义

**报告输出**：节点分析中标注 `[通用模式: UP-03 双模操作]`。在 §5.1 列出。在 §5.3 评价双模维护成本。

---

## UP-04: 数据驱动Web表单填充

**一句话描述**：Excel 数据行 → Python 解析 → 逐字段 JS 注入 → 表单提交。

**必须命中（AND）**：
- [ ] `pd.read_excel()` 读取含表单字段名的 Excel（列名即字段名）
- [ ] 存在 `browser_inject_js_code` 节点使用 `input.value = ...` 或 `dispatchEvent` 模式
- [ ] JS 注入的变量值来自 Excel 数据行的字段值

**可选信号（OR）**：
- [ ] 存在 `process_iterator` 逐行遍历 Excel 数据
- [ ] JS 代码包含 `querySelector` 定位表单输入框
- [ ] 有重复/新增/修改多个子流程共享同一批 JS 注入节点

**报告输出**：节点分析中标注 `[通用模式: UP-04 数据驱动Web表单填充]`。

---

## UP-05: 逐规则分表输出

**一句话描述**：按优先级规则链对数据逐层筛选，每层筛选结果写入单独 Sheet。

**必须命中（AND）**：
- [ ] 存在 >=3 个顺序 `df[condition]` 或 `df.query()` 筛选操作
- [ ] 每个筛选结果写入不同 Sheet（`df.to_excel(sheet_name=...)` 含不同 sheet_name）
- [ ] 每轮筛选后保留 remainder（未命中数据）传给下一轮

**可选信号（OR）**：
- [ ] 规则定义在 `process_assignment` 节点或配置文件而非代码中
- [ ] Sheet 名含规则分类含义

**报告输出**：节点分析中标注 `[通用模式: UP-05 逐规则分表输出]`。在 §5.3 评价规则是否可配置化。

---

## 模式维护记录

| 日期 | 操作 | 模式 |
|------|------|------|
| 2026-06-23 | 创建 | UP-01, UP-02, UP-03, UP-04, UP-05 |

### last_hit tracking

| 模式 | last_hit | 连续未命中次数 |
|------|----------|:---:|
| UP-01 | 2026-06-23 | 0 |
| UP-02 | 2026-06-23 | 0 |
| UP-03 | 2026-06-23 | 0 |
| UP-04 | 2026-06-23 | 0 |
| UP-05 | 2026-06-23 | 0 |
