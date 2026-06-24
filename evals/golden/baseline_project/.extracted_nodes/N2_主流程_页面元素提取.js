/**
 * @node: N2 — 页面元素提取
 * @id: node_js_001
 * @flow: 主流程.json
 * @input:  (无)
 * @output: result → string
 * @lines: 2
 * @hash: 4c0cae2429b2
 * @desc:   依赖: DOM查询。单行工具脚本。DOM文本提取。数据提取
 */


var result = document.querySelector('.title').textContent;
return result;
