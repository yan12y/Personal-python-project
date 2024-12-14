"""
该模块定义了一个实时数据管理线程，用于批处理实时数据队列中的数据并保存到MySQL数据库中。
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
    实时数据管理线程，负责批处理实时数据队列中的数据并保存到MySQL数据库中。

    该函数周期性地检查全局变量 `global_vars.r_d` 中的实时数据队列，并将队列中的数据批量写入到MySQL数据库中。
    如果遇到任何错误，它会发送邮件通知并记录日志。

    参数：
    - host: MySQL数据库主机地址。
    - port: MySQL数据库端口号，默认为3306。
    - username: MySQL数据库用户名。
    - password: MySQL数据库密码。
    - database: 要操作的数据库名称。
    - sender: QQ邮件发送者邮箱地址，用于发送错误通知。
    - receiver: QQ邮件接收者邮箱地址，用于接收错误通知。
    - sender_password: 发送者QQ邮箱的授权码，用于邮件发送验证。

    返回：
    - 无返回值，但会将实时数据保存到数据库，并在出现错误时通过邮件通知。

    异常处理：
    - 如果在数据库写入过程中发生异常，会通过 `send_email` 函数发送错误通知邮件，
      并记录日志到 `global_vars.lq` 日志队列中。
      如果连续多次失败，会设置 `global_vars.s_finished_event` 为 True 以停止所有线程。
    """
    global_vars.lq.push(('实时数据管理线程-状态信息','info','实时数据管理线程开始运行'))
    time.sleep(30)
    while True:
        try:
            if global_vars.s_finished_event:  # 事件对象被设置，说明s进程结束

                # 确保r_d的数据被完全写入数据库
                real_time_data(global_vars.r_d, host, port, username, password, database, global_vars.data_table_name)
                global_vars.lq.push(('实时数据管理线程-状态信息','info','实时数据管理线程结束运行'))
                break

            if real_time_data(global_vars.r_d, host, port, username, password, database, global_vars.data_table_name):
                time.sleep(6 * 60)
            else:
                send_email(sender, receiver, sender_password, subject='来自okx自动化策略程序的运行错误的提醒:',
                           content='线程：real_time_data_manager_thread\n实时数据批处理失败\n请检查网络')

                global_vars.s_finished_event = True
                break

        except Exception as e:

            global_vars.s_finished_event = True
            global_vars.lq.push(('实时数据管理线程-错误信息', 'error', '实时数据管理线程出现错误，错误信息：' + str(e)))
            break
