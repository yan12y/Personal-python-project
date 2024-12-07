"""
这个模块定义了一个开关线程，用于根据MySQL数据库中的'switch'表的值控制程序的退出和运行状态。
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
    这个管理函数会定时从mysql中的database数据库中的'switch'表中获取最后一行的值作为控制程序的退出，当获取的值为1时，它会更改should_exit为False(表示程序保持运行),
    当当获取的值为0时，更改为False(表示程序停止运行)
    :param host:
    :param username:
    :param password:
    :param database:
    :param port:
    :param table:
    :return:
    """
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
                    global_vars.lq.push(('程序状态', 'Info', '程序将停止运行'))

            time.sleep(30)
        except:
            global_vars.s_finished_event = True
            raise Exception
