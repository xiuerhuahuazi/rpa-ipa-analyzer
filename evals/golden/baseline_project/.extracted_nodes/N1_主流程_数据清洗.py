"""
@node: N1 — 数据清洗
@id: node_python_001
@flow: 主流程.json
@input:  file_path ← C:/data/input.xlsx, out_path ← C:/data/output.xlsx
@output: df → DataFrame
@lines: 5
@hash: e5036c3530df
@desc:   依赖: pandas。读取Excel | 写入Excel。简短处理
"""

import pandas as pd
df = pd.read_excel(file_path)
df = df.dropna()
df.to_excel(out_path,index=False)
print('Done')
