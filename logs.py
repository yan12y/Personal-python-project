"""
这个模块定义了一个日志队列类和相关的日志处理函数。具体功能包括：

创建日志表。
记录程序的状态和操作信息到日志表中。
将日志队列中的日志记录同步到MySQL数据库。
"""

import pymysql


# 定义一个用来记录日志的队列类
class LogQueue:
    """
    一个用来记录日志的队列。
    """

    def __init__(self):
        self.logs = []

    def push(self, log: tuple) -> None:
        """
        将一条日志记录入队。
        :param log: 一个元组，代表一条日志记录，例如：('创建日志表', 'Success', '创建表成功')
        """
        self.logs.append(log)

    def pop(self) -> tuple:
        """
        弹出一条日志记录。
        :return: 元组形式的日志记录
        """
        return self.logs.pop(0)


def create_log_table(mysql_host: str, mysql_port: int, mysql_username: str, mysql_password: str, mysql_database: str,
                     mysql_log_table: str) -> bool:
    """
    登录MySQL数据库，并在指定数据库中创建日志表。
    :param mysql_host: 数据库主机
    :param mysql_port: 端口
    :param mysql_username: 数据库用户名
    :param mysql_password: 密码
    :param mysql_database: 数据库名
    :param mysql_log_table: 要创建的表格名
    :return: True 表示创建成功，False 表示创建失败
    """
    try:
        with pymysql.connect(host=mysql_host, port=mysql_port, user=mysql_username, password=mysql_password,
                             ) as client:

            # 创建游标
            cursor = client.cursor()
            # 创建数据库
            create_db_sql = f"""CREATE DATABASE IF NOT EXISTS {mysql_database}"""
            # 执行创建数据库的SQL语句
            cursor.execute(create_db_sql)
            # 提交事务
            client.commit()
            # 使用新创建的数据库
            client.select_db(mysql_database)

            create_logs_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {mysql_log_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action VARCHAR(255),
                    status VARCHAR(50),
                    details TEXT
                )
            """
            cursor.execute(create_logs_table_sql)
            log_action(mysql_log_table, cursor, '创建新日志表', 'Success', '创建新日志表成功')
            return True
    except Exception as e:
        print(f"创建日志表失败: {e}")
        return False


def log_action(table_name: str, cursor, action: str, status: str, details: str) -> None:
    """
    在日志表中记录程序的状态和操作信息。
    :param table_name: 日志的表名
    :param cursor: 游标对象
    :param action: 执行的动作
    :param status: 执行的状态
    :param details: 动作描述
    """
    insert_log_sql = f"""
        INSERT INTO {table_name} (action, status, details) VALUES (%s, %s, %s)
    """
    cursor.execute(insert_log_sql, (action, status, details))
    cursor.connection.commit()


def log_to_mysql(mysql_host: str, mysql_port: int, mysql_username: str, mysql_password: str, mysql_database: str,
                 mysql_log_table: str, max_logs: int, log_queue: LogQueue) -> bool:
    """
    从日志队列中取出最多 max_logs 条记录并存入数据库的日志表中。
    :param mysql_host: 数据库主机
    :param mysql_port: 端口
    :param mysql_username: 数据库用户名
    :param mysql_password: 密码
    :param mysql_database: 数据库名
    :param mysql_log_table: 日志表名
    :param max_logs: 最多取出多少条日志记录
    :param log_queue: 日志队列对象
    :return: True 表示完成该操作，False 表示失败
    """
    try:
        with pymysql.connect(host=mysql_host, port=mysql_port, user=mysql_username, password=mysql_password,
                             database=mysql_database) as client:
            cursor = client.cursor()
            for _ in range(min(max_logs, len(log_queue.logs))):
                log = log_queue.pop()
                log_action(mysql_log_table, cursor, log[0], log[1], log[2])
            return True
    except Exception as e:
        print(f"日志同步失败: {e}")
        return False
