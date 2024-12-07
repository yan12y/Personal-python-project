"""
这个模块提供了与MySQL数据库相关的操作功能。具体包括：

将数据保存到MySQL数据库。
从数据库中获取数据并转换为DataFrame。
获取前一天的收盘价。
实时数据的批量写入数据库操作。
创建控制程序开关的表。

"""

import time
from datetime import datetime
# 内置模块
from datetime import timedelta

import pandas as pd
# 第三方模块
import pymysql

# 自定义模块
from myokx import MyOkx


def sava_all_data_to_mysql(start_date: str, instId: str, username: str, password: str, host: str, database: str,
                           table: str, port: int = 3306) -> None:
    """
        这个方法会从Okx中获取你给定的开始时间：start_date到现在所有的日数据到mysql数据库中去。注意访问Okx需要连接vpn。
    :param start_date: 开始时间，格式为：%Y-%m-%d,注意获取的数据不包括开始时间的数据
    :param instId:交易币对
    :param username: 数据库用户名
    :param password: 数据库密码
    :param host: 数据库主机
    :param port: 数据库端口号，默认为：3306
    :param database: 数据名
    :param table: 表名
    :return:
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")  # 将字符串转换为时间对象

    end_date_obj = start_date_obj + timedelta(days=31)

    " 一次获取30天的数据 "
    with pymysql.connect(host=host, port=port, user=username, password=password) as client:  # 连接数据库
        # 创建游标
        cursor = client.cursor()
        # 创建数据库
        create_db_sql = f"""CREATE DATABASE IF NOT EXISTS {database}"""
        # 执行创建数据库的SQL语句
        cursor.execute(create_db_sql)
        # 提交事务
        client.commit()
        # 使用新创建的数据库
        client.select_db(database)
        # 创建表
        create_table_sql = f"""CREATE TABLE IF NOT EXISTS {table} (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                时间 DATE,
                                开盘价 FLOAT,
                                最高价格 FLOAT,
                                最低价格 FLOAT,
                                收盘价 FLOAT,
                                成交量 FLOAT,
                                成交额 FLOAT
                                )"""
        cursor.execute(create_table_sql)
        o = MyOkx()

        while True:
            # 将数据转换为字符串格
            start_date = start_date_obj.strftime("%Y-%m-%d")
            end_date = end_date_obj.strftime("%Y-%m-%d")

            data = o.get_closing_prices(start_date, end_date, instId)
            if data is None:
                return
            for item in data:
                # 首先先通过时间查询，如果存在就跳过
                sql = f"SELECT * FROM {table} WHERE 时间='{item[0]}'"
                cursor.execute(sql)
                if cursor.fetchone() is None:

                    # # 插入语句
                    insert_sql = (
                        f"INSERT INTO {table} (时间, 开盘价, 最高价格, 最低价格, 收盘价, 成交量, 成交额) VALUES (%s, %s, %s, %s, "
                        f"%s, %s, %s)")
                    cursor.execute(insert_sql, (
                        item[0], float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5]),
                        float(item[6])))
                    client.commit()  # 提交事务
                else:
                    return

            # 更新新的时间时间对象
            start_date_obj = end_date_obj - timedelta(days=1)  # 需要减一天
            end_date_obj = start_date_obj + timedelta(days=31)
            time.sleep(4)


def get_data_from_mysql(username: str, password: str, host: str, database: str, table: str,
                        port: int = 3306) -> pd.DataFrame:
    """
    这个方法从数据库中获取数据，返回一个DataFrame。
    :param username: 数据库用户名
    :param password: 数据库密码
    :param host: 数据库主机
    :param port :数据库端口号，默认为：3306
    :param database: 数据库名
    :param table: 表名
    :return: 返回一个DataFrame。
    """
    with pymysql.connect(host=host, port=port, user=username, password=password, database=database) as client:
        df = pd.read_sql(f"SELECT * FROM {table}", con=client)
        return df


def get_late_date_prices(username: str, password: str, host: str, database: str, table: str) -> float:
    """
    这个方法从数据库中获取前一天的收盘价，返回一个float类型数据。
    :param username: 数据库用户名
    :param password: 数据库密码
    :param host: 数据库主机
    :param database: 数据库名
    :param table: 表名
    :return: 返回float型。对收盘价，时间
    """
    with pymysql.connect(host=host, user=username, password=password, database=database) as client:
        df = pd.read_sql(f"SELECT * FROM {table} ORDER BY 时间 DESC LIMIT 1", con=client)
        price = float(df['收盘价'])
        return price


def real_time_data(r_d: list, host: str, port: int, username: str, password: str, database: str, table: str):
    """
    批量将r_d中的数据写入数据库
    r_d是一个列表，它包含了以下内容数据：
    r_d =[[date,current_price,last_data_price,sleep_time,u_p_1,]]
    date 当前时间
    current_price:float 当前的价格数据
    last_p:float 上一的价格数据
    sleep_time:int 下一次休眠的时间间隔数据
    u_p_1: 多头开仓涨幅区间1（1.5%,5%）计数器
    u_p_2: 多头开仓涨幅区间2（5%,10%）计数器
    u_p_3: 多头开仓涨幅区间3（10%,15%）计数器
    u_p_4: 多头开仓涨幅区间4（15%,25%）计数器
    d_p_1: 空头开仓跌幅区间1（1.5%,5%）计数器
    d_p_2: 空头开仓跌幅区间2（5%,10%）计数器
    d_p_3: 空头开仓跌幅区间3（10%,15%）计数器
    d_p_4: 空头开仓跌幅区间4（15%,25%）计数器
    """
    with pymysql.connect(host=host, port=port, user=username, password=password) as client:  # 连接数据库
        # 创建游标
        cursor = client.cursor()
        # 创建数据库
        create_db_sql = f"""CREATE DATABASE IF NOT EXISTS {database}"""
        # 执行创建数据库的SQL语句
        cursor.execute(create_db_sql)
        # 提交事务
        client.commit()
        # 使用新创建的数据库
        client.select_db(database)
        # 创建表
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS `{table}` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `当前时间` DATETIME,
            `当前价格` FLOAT,
            `上一次价格` FLOAT,
            `较昨天的涨跌幅` FLOAT,
            `较上一次的涨跌幅` FLOAT,
            `上一次五个当前价格的平均值` FLOAT,
            `当前五个当前价格的平均值` FLOAT,
            `上一次主流货币当前价格标准化均值` FLOAT,
            `当前主流货币当前价格标准化均值` FLOAT,
            `上一次bidSz` FLOAT,
            `当前bidSz` FLOAT,
            `上一次askSz` FLOAT,
            `当前askSz` FLOAT,
            `上一次24小时交易量` FLOAT,
            `当前24小时交易量` FLOAT,
            `开多计数` INT,
            `开空计数` INT,
            `下一次休眠时间` INT,
            `多仓涨幅区间1次数` INT,
            `多仓涨幅区间2次数` INT,
            `多仓涨幅区间3次数` INT,
            `多仓涨幅区间4次数` INT,
            `空仓跌幅区间1次数` INT,
            `空仓跌幅区间2次数` INT,
            `空仓跌幅区间3次数` INT,
            `空仓跌幅区间4次数` INT,
            `long_place_downlimit` FLOAT,
            `long_place_uplimit` FLOAT,
            `short_place_downlimit` FLOAT,
            `short_place_uplimit` FLOAT, 
            `当前仓位数量` FLOAT,
            `交易类型` INT
        )
        """
        cursor.execute(create_table_sql)

        insert_sql = f"""
        INSERT INTO `{table}` (
            `当前时间`,
            `当前价格`,
            `上一次价格`,
            `较昨天的涨跌幅`,
            `较上一次的涨跌幅`,
            `上一次五个当前价格的平均值`,
            `当前五个当前价格的平均值`,
            `上一次主流货币当前价格标准化均值`,
            `当前主流货币当前价格标准化均值`,
            `上一次bidSz`,
            `当前bidSz`,
            `上一次askSz`,
            `当前askSz`,
            `上一次24小时交易量`,
            `当前24小时交易量`,
            `开多计数`,
            `开空计数`,
            `下一次休眠时间`,
            `多仓涨幅区间1次数`,
            `多仓涨幅区间2次数`,
            `多仓涨幅区间3次数`,
            `多仓涨幅区间4次数`,
            `空仓跌幅区间1次数`,
            `空仓跌幅区间2次数`,
            `空仓跌幅区间3次数`,
            `空仓跌幅区间4次数`,
            `long_place_downlimit`,
            `long_place_uplimit`,
            `short_place_downlimit`,
            `short_place_uplimit`,
            `当前仓位数量`,
            `交易类型`
        ) VALUES (
            %s, %s, %s, %s, %s,  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        # 批量插入数据
        while True:
            try:
                d = r_d.pop(0)
                cursor.execute(insert_sql, tuple(d))
            except Exception as e:
                if isinstance(e, IndexError):
                    # 提交事务
                    client.commit()
                    return True
                else:
                    return False


def create_control_program_switch_table(host: str, username: str, password: str, database: str, port: int = 3306,
                                        table: str = 'switch'):
    """
    这个函数会在相应的数据库中创建一个控制程序开关的表
    :param host:
    :param port:
    :param username:
    :param password:
    :param database:
    :param table:
    :return:
    """
    with pymysql.connect(host=host, port=port, user=username, password=password) as client:  # 连接数据库
        # 创建游标
        cursor = client.cursor()
        # 创建数据库
        create_db_sql = f"""CREATE DATABASE IF NOT EXISTS {database}"""
        # 执行创建数据库的SQL语句
        cursor.execute(create_db_sql)
        # 提交事务
        client.commit()
        # 使用新创建的数据库
        client.select_db(database)
        # 创建表
        create_table_sql = f"""
           CREATE TABLE IF NOT EXISTS `{table}` (
       id INT AUTO_INCREMENT PRIMARY KEY,
       `程序开关` INT CHECK (`程序开关` IN (0, 1))
    );
        """
        cursor.execute(create_table_sql)

        # 插入数据
        insert_sql = f"""
        INSERT INTO `{table}` (`程序开关`) VALUES (%s)
        """
        cursor.execute(insert_sql, 1)
        client.commit()
