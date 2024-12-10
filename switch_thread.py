"""
该模块定义了一个开关线程，用于根据MySQL数据库中的'switch'表的值控制程序的退出和运行状态。
"""

" 内置模块 "
import time

" 第三方模块 "
import pandas as pd
import pymysql

" 自定义模块 "
import global_vars


def switch_thread(host: str, username: str, password: str, database: str, port: int = 3306, table: str = 'switch'):
    """
       开关线程，用于根据MySQL数据库中的'switch'表的值控制程序的退出和运行状态。

       该函数定期从MySQL数据库中查询'switch'表的最新值，以决定程序是否应该继续运行。
       如果'switch'表中的值为0，则程序将停止运行；如果为1，则程序继续运行。

       参数：
       - host: MySQL数据库主机地址。
       - username: MySQL数据库用户名。
       - password: MySQL数据库密码。
       - database: 要查询的数据库名称。
       - port: MySQL数据库端口号，默认为3306。
       - table: 存储程序开关状态的表名，默认为'switch'。

       返回：
       - 无返回值，但会根据数据库中的值改变程序的运行状态。

       异常处理：
       - 如果在数据库查询过程中发生异常，会记录错误信息到日志队列 `global_vars.lq` 中，并设置 `global_vars.s_finished_event` 为 True 以停止程序运行。
       """
    global_vars.lq.push(('程序开关管理线程-状态信息', 'info', '程序开关管理线程启动'))
    time.sleep(30)
    while True:
        try:
            if global_vars.s_finished_event:
                break
            with pymysql.connect(host=host, user=username, password=password, database=database, port=port) as client:
                df = pd.read_sql(f"SELECT id,程序开关 FROM {table} ORDER BY id DESC LIMIT 1", con=client)
                re = int(df['程序开关'].iloc[0])
                if re == 0:
                    global_vars.s_finished_event = True
                    global_vars.next_model_train_sleep_time = 1
                    global_vars.lq.push(('程序状态', 'Info', '程序将停止运行'))

            time.sleep(30)
        except Exception as e:
            global_vars.s_finished_event = True
            global_vars.lq.push(('程序开关管理线程-错误信息', 'info', f'程序开关管理线程错误：{e}'))
            break
