"""
这个模块声明了全局变量，用于在程序的不同部分之间共享状态和数据。具体包括：

控制线程结束的事件对象。
日志队列和实时数据队列，用于存储日志信息和实时数据。
日志表名和实时数据表名，用于根据不同日期创建对应的表。
@Time: 2024/12/6 9:45
@Author: ysh
@File: global_vars.py
"""
import pandas as pd

" 内置模块 "
import threading

" 自定义模块 "
from logs import LogQueue

# 创建一个事件对象:当这个事件被触发，则会触发所有线程的结束
s_finished_event: bool = False

# 这个是日志队列，可以共享日志信息给日志管理线程，让日志管理线程将日志信息上传至数据库中。
lq: LogQueue = LogQueue()

# 这个是实时数据队列，存储的是实时数据，当有新的数据时，会通过队列的方式，发送给策略管理线程，由策略管理线程来处理上传到数据库中。
r_d = []  # 这个是实时数据队列，

# 日志表名，strategy_manager_thread会根据不同日期创建不同日期的日志表
log_table_name: str

# 实时数据表名，strategy_manager_thread会根据不同日期创建不同日期的实时数据表名
data_table_name: str

# 模型训练线程给出的评分结果最好的模型对象,初始化为None
best_model: object = None

# 模型训练线程给出的没有进行过标准化的特征数据集
attr_df: pd.DataFrame
