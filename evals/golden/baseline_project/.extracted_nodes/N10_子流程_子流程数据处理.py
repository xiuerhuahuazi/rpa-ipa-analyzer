"""
@node: N10 — 子流程数据处理
@id: sub_python_001
@flow: 子流程.json
@input:  input_file ← data.xlsx
@output: df → DataFrame
@lines: 3
@hash: 07a6c627e528
@desc:   依赖: pandas。读取Excel。单行工具脚本
"""

import pandas as pd
df = pd.read_excel(input_file)
print(df.shape)
