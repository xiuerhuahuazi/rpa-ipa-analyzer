# Domain-Specific RPA Pattern Reference

> 领域参考案例，仅供人类阅读。不参与自动匹配。当分析同行业/同系统项目时可参考。

## 案例 1：系统 Token 提取 + API 调用

**领域**：系统
**组件链**：`browser_inject_js_code` (StorageUtils 提取 sessionStorage) → `script_python_execute` (bearer_token → HTTP 请求)
**参考价值**：展示"浏览器取 Token → Python 调用 API"的安全模式

## 案例 2：OCR 验证码自动识别

**领域**：登录页
**组件链**：`script_python_execute` (ddddocr 库 classify) → `keyboard_text_input` (OCR 结果填入表单)
**参考价值**：验证码场景的投入产出评估（OCR 准确率 vs 人工处理）

## 案例 3：API 证书验证

**领域**：部门
**组件链**：`script_python_execute` (requests.Session + .gov.cn 域名) → `process_iterator` (批量 vs 单条)
**参考价值**：API 的 Cookie 管理 + CAPTCHA 处理

## 案例 4：离线依赖安装

**领域**：air-gapped RPA 部署环境
**组件链**：`script_python_execute` (subprocess pip install .whl) → 后续 import 使用
**参考价值**：离线部署的依赖管理策略

## 案例 5：坐标点击回退

**领域**：非标准 UI 控件
**组件链**：`ui_get_target_location` (获取坐标) → `script_python_execute` (pyautogui.click)
**参考价值**：当直接 UI 选择器失效时的降级方案

---

归档日期：2026-06-23。原 14 个模式中通用结构模式升级为 patterns_universal.md 的 UP-01 至 UP-05。
