"""
这个模块是程序的运行入口，负责连接MySQL数据库、获取参数、启动和管理各个线程（日志管理线程、实时数据管理线程、策略管理线程、开关线程）。
"""

" 内置模块 "
from threading import Thread

" 第三方模块 "
import pymysql

" 自定义模块 "
from logs_manager_thread import logs_manager_thread
from real_time_data_manager_thread import real_time_data_manager_thread
from strategy_manager_thread import strategy_manager_thread
from switch_thread import switch_thread

if __name__ == '__main__':
    # 连接MySQL数据库
    mydb = pymysql.connect(
        host="101.34.59.205",
        user="云服务器mysql",  # 此账户只有读权限
        password="yshhsq31",
        database="自动化交易程序配置参数"
    )

    mycursor = mydb.cursor()

    # 从strategy_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM strategy_manager_thread_arguments")
    result_strategy = mycursor.fetchone()
    strategy_thread = None
    if result_strategy:
        strategy_args = {
            'mysql_host': result_strategy[1],
            'mysql_username': result_strategy[2],
            'mysql_password': result_strategy[3],
            'mysql_coin_database': result_strategy[4],
            'mysql_coin_day_date_table': result_strategy[5],
            'okx_api_key': result_strategy[6],
            'okx_secret_key': result_strategy[7],
            'okx_passphrase': result_strategy[8],
            'instId': result_strategy[9],
            'leverage': int(result_strategy[10]),
            'sender': result_strategy[11],
            'receiver': result_strategy[12],
            'sender_password': result_strategy[13],
            'place_position_nums': result_strategy[14],
            'place_uplimit': (result_strategy[15]),
            'place_downlimit': (result_strategy[16]),
            'mysql_port': (result_strategy[17]),
            'sz': result_strategy[18],
            'l_s1': result_strategy[19],
            'l_s2': result_strategy[20],
            'l_s3': result_strategy[21],
            'l_s4': result_strategy[22],
            'l_e1': result_strategy[23],
            'l_e2': result_strategy[24],
            'l_e3': result_strategy[25],
            'l_e4': result_strategy[26],
            's_s1': result_strategy[27],
            's_s2': result_strategy[28],
            's_s3': result_strategy[29],
            's_s4': result_strategy[30],
            's_e1': result_strategy[31],
            's_e2': result_strategy[32],
            's_e3': result_strategy[33],
            's_e4': result_strategy[34],
            'l_c_limit': result_strategy[35],
            's_c_limit': result_strategy[36],
            'limit_uplRatio': result_strategy[37],
        }
        strategy_thread = Thread(target=strategy_manager_thread, kwargs=strategy_args)

    # 从logs_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM logs_manager_thread_arguments")
    result_logs = mycursor.fetchone()
    logs_thread = None
    if result_logs:
        logs_args = {
            'mysql_host': result_logs[1],
            'mysql_port': result_logs[2],
            'mysql_username': result_logs[3],
            'mysql_password': result_logs[4],
            'mysql_database': result_strategy[4],
            'sender': result_logs[5],
            'receiver': result_logs[6],
            'sender_password': result_logs[7],
            'fq': result_logs[8]
        }
        logs_thread = Thread(target=logs_manager_thread, kwargs=logs_args)

    # 从real_time_data_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM real_time_data_manager_thread_arguments")
    result_real_time = mycursor.fetchone()
    real_time_thread = None
    if result_real_time:
        real_time_args = {
            'host': result_real_time[1],
            'port': result_real_time[2],
            'username': result_real_time[3],
            'password': result_real_time[4],
            'database': result_strategy[4],
            'sender': result_real_time[5],
            'receiver': result_real_time[6],
            'sender_password': result_real_time[7]
        }
        real_time_thread = Thread(target=real_time_data_manager_thread, kwargs=real_time_args)

    switch_thread = Thread(target=switch_thread,
                           args=(
                           result_logs[1], result_logs[3], result_logs[4], result_strategy[4], result_real_time[2]))

    mycursor.close()
    mydb.close()

    # 启动线程
    if strategy_thread:
        strategy_thread.start()

    if logs_thread:
        logs_thread.start()

    if real_time_thread:
        real_time_thread.start()

    if switch_thread:
        switch_thread.start()

    # 阻塞主线程
    if strategy_thread:
        strategy_thread.join()

    if logs_thread:
        logs_thread.join()

    if real_time_thread:
        real_time_thread.join()

    if switch_thread:
        switch_thread.join()
