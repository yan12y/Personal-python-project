"""
该模块是程序的运行入口，负责连接MySQL数据库、获取参数、启动和管理各个线程（日志管理线程、实时数据管理线程、策略管理线程、开关线程）。
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
import global_vars
from model_train_thread import model_train_thread

if __name__ == '__main__':

    global_vars.lq.push(('程序状态', 'Info', '程序开始启动'))

    # 连接MySQL数据库
    mydb = pymysql.connect(
        host="101.34.59.205",
        user="yang",  # 此账户只有读权限
        password="yshhsq31",
        database="自动化交易程序配置参数"
    )

    mycursor = mydb.cursor()

    # 从strategy_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM 自动化程序参数")
    result = mycursor.fetchone()

    if result:
        # 创建策略管理线程
        strategy_args = {
            'mysql_host': result[1],
            'mysql_username': result[2],
            'mysql_password': result[3],
            'mysql_coin_database': result[4],
            'mysql_coin_day_date_table': result[5],
            'okx_api_key': result[6],
            'okx_secret_key': result[7],
            'okx_passphrase': result[8],
            'instId': result[9],
            'leverage': int(result[10]),
            'sender': result[11],
            'receiver': result[12],
            'sender_password': result[13],
            'place_position_nums': result[14],
            'place_uplimit': (result[15]),
            'place_downlimit': (result[16]),
            'mysql_port': (result[17]),
            'sz': result[18],
            'l_s1': result[19],
            'l_s2': result[20],
            'l_s3': result[21],
            'l_s4': result[22],
            'l_e1': result[23],
            'l_e2': result[24],
            'l_e3': result[25],
            'l_e4': result[26],
            's_s1': result[27],
            's_s2': result[28],
            's_s3': result[29],
            's_s4': result[30],
            's_e1': result[31],
            's_e2': result[32],
            's_e3': result[33],
            's_e4': result[34],
            'l_c_limit': result[35],
            's_c_limit': result[36],
            'limit_uplRatio': result[37],
            'lower_take_profit':result[39]
        }


        strategy_thread = Thread(target=strategy_manager_thread, kwargs=strategy_args)

        # 创建日志管理线程
        logs_args = {
            'mysql_host': result[1],
            'mysql_port':result[17],
            'mysql_username': result[2],
            'mysql_password': result[3],
            'mysql_database': result[4],
            'sender': result[11],
            'receiver': result[12],
            'sender_password': result[13],
            'fq': 100
        }
        logs_thread = Thread(target=logs_manager_thread, kwargs=logs_args)

        # 创建实时数据管理线程
        real_time_args = {
            'host': result[1],
            'port': result[17],
            'username': result[2],
            'password': result[3],
            'database': result[4],
            'sender': result[11],
            'receiver': result[12],
            'sender_password': result[13]
        }
        real_time_thread = Thread(target=real_time_data_manager_thread, kwargs=real_time_args)

        #创建开关管理线程
        switch_args = {
            'host': result[1],
            'username': result[2],
            'password': result[3],
            'database': result[4],
            'port': result[17],
            'table': 'switch',
        }
        switch_thread = Thread(target=switch_thread,
                               kwargs=switch_args)

        # 创建模型训练线程
        model_train_args = {
                'sender': result[11],
                'receiver': result[12],
                'mail_password': result[13],
                'host': result[1],
                'username': result[2],
                'password': result[3],
                'database_name': result[4],
                'start_date_str': result[38],
                'port': result[17]
        }
        model_train_thread = Thread(target=model_train_thread, kwargs=model_train_args)

        mycursor.close()
        mydb.close()


        # 启动线程
        strategy_thread.start()
        logs_thread.start()
        real_time_thread.start()
        switch_thread.start()
        model_train_thread.start()

        global_vars.lq.push(('程序状态', 'Info', '程序成功启动'))
        # 等待线程结束
        strategy_thread.join()
        logs_thread.join()
        real_time_thread.join()
        switch_thread.join()
        model_train_thread.join()

