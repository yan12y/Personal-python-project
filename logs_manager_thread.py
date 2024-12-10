"""
该模块定义了一个日志管理线程，用于批处理日志队列中的日志并保存到MySQL数据库中。
"""

" 内置模块 "
import time

" 自定义模块 "
from logs import log_to_mysql
from mymail import send_email
import global_vars


# 日志管理线程，批处理日志队列里面的日志到MySQL数据库中的函数
def logs_manager_thread(mysql_host: str, mysql_username: str, mysql_password: str, mysql_database: str,
                        sender: str, receiver: str, sender_password: str,
                        fq: int, mysql_port: int = 3306) -> None:
    """
    这是一个日志管理线程，它会批处理日志队列里面的日志到mysql数据库中
    :param mysql_host: 数据库主机
    :param mysql_port :端口,默认是3306
    :param mysql_username: 数据库用户名
    :param mysql_password: 密码
    :param mysql_database: 数据库名
    :param sender:QQ邮件发送者
    :param receiver:QQ邮件接收者
    :param sender_password:QQ邮件发送者的密码（授权码）
    :param fq: 一次批处理的日志记录数量
    :return:
    """

    global_vars.lq.push(('日志管理线程-状态信息', 'info', '日志管理线程启动'))
    time.sleep(30)
    while True:
        try:
            if global_vars.s_finished_event:  # 事件对象被设置，说明s进程结束
                # 确保r_d的数据被完全写入数据库
                while not global_vars.lq:
                    log_to_mysql(mysql_host=mysql_host, mysql_username=mysql_username, mysql_password=mysql_password,
                                 mysql_database=mysql_database, mysql_log_table=global_vars.log_table_name, max_logs=fq,
                                 log_queue=global_vars.lq,
                                 mysql_port=mysql_port)
                    time.sleep(5)
                print("日志管理线程停止")
                break

            i = 0  # 重试计数器
            while True:
                if log_to_mysql(mysql_host=mysql_host, mysql_username=mysql_username, mysql_password=mysql_password,
                                mysql_database=mysql_database, mysql_log_table=global_vars.log_table_name, max_logs=fq,
                                log_queue=global_vars.lq,
                                mysql_port=mysql_port) is False:  # 该函数可以一次可以批量处理fq条日志到数据库中
                    if i < 3:  # 最多重试3次
                        print("批量处理日志信息到mysql数据库失败，10秒后重试")
                        i += 1
                        time.sleep(10)
                    else:
                        send_email(sender, receiver, sender_password, subject='来自okx自动化策略程序的运行错误的提醒:',
                                   content='线程：logs_manager_thread\n日志批处理失败\n请检查网络')

                        global_vars.s_finished_event = True

                else:
                    break  # 如果批量处理日志成功，就跳出循环。

            time.sleep(5 * 60)  # 五分钟执行一次
        except:
            global_vars.s_finished_event = True
            raise Exception
