"""
这个模块定义了一个实时数据管理线程，用于批处理实时数据队列中的数据并保存到MySQL数据库中。
@Time: 2024/11/20 9:45
@Author: ysh
@File: real_time_data_manager_thread.py
"""

" 内置模块 "
import time

" 第三方模块 "
import global_vars
from mymail import send_email
from mysqldata import real_time_data


def real_time_data_manager_thread(host: str, port: int, username: str, password: str, database: str,
                                  sender: str, receiver: str, sender_password: str,
                                  ):
    """
    这是一个实时数据管理线程，它会批处理实时数据队列里面的数据到mysql数据库中
    :param: host：数据库服务器的主机地址，指定了要连接的 MySQL 服务器的位置，例如101.34.59.205。
    :param: port：数据库服务器的端口号，默认为3306，用于建立与 MySQL 服务器的连接。
    :param: username：连接数据库的用户名，拥有对指定数据库的操作权限，如云服务器mysql。
    :param: password：连接数据库的用户密码，如yshhsq31。
    :param: database：要操作的数据库名称，这里是wld数据库，数据将被存储到该数据库中。
    :param: table：存储实时数据的表名（虽然代码中未显示此参数在函数内的使用，但推测用于指定数据存储的目标表）。
    :param: sender：QQ 邮件发送者的邮箱地址，用于在出现错误时发送通知邮件，如2941064305@qq.com。
    :param: receiver：QQ 邮件接收者的邮箱地址，通常是与程序相关的维护人员或监控人员的邮箱，如2941064305@qq.com。
    :param: sender_password：QQ 邮件发送者的密码（授权码），用于通过代码登录邮箱发送邮件，如mxalwtgimsdbddfi。
    """

    time.sleep(30)
    while True:
        try:
            if global_vars.s_finished_event:  # 事件对象被设置，说明s进程结束

                # 确保r_d的数据被完全写入数据库
                real_time_data(global_vars.r_d, host, port, username, password, database, global_vars.data_table_name)
                break

            if real_time_data(global_vars.r_d, host, port, username, password, database, global_vars.data_table_name):
                time.sleep(5 * 60)
            else:
                send_email(sender, receiver, sender_password, subject='来自okx自动化策略程序的运行错误的提醒:',
                           content='线程：real_time_data_manager_thread\n实时数据批处理失败\n请检查网络')
                break
        except:

            global_vars.s_finished_event = True
            raise Exception
