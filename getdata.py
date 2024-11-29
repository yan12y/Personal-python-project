import ccxt
import numpy as np
import pandas as pd
import time
import pymysql

def fetch_ohlcv(symbol, start_date, end_date, timeframe, exchange_name='okx'):
    """
    获取指定时间范围内的交易对的K线数据
    :param exchange_name: 交易所名称，例如 'okx'
    :param symbol: 交易对，例如 'BTC/USDT' 或 'BTC/USDT:SWAP'
    :param start_date: 开始时间，格式为 'YYYY-MM-DD'
    :param end_date: 结束时间，格式为 'YYYY-MM-DD'
    :param timeframe: K线时间周期，例如 '1m', '5m', '1h', '1d'
    :return: DataFrame，包含指定时间范围内的K线数据
    """
    # 创建交易所对象
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class()

    # 将开始时间和结束时间转换为毫秒时间戳
    start_time = int(time.mktime(time.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000
    end_time = int(time.mktime(time.strptime(end_date + " 00:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000

    # 初始化一个空的 DataFrame 用于存储所有数据
    all_data = []

    # 初始时间设置
    current_time = start_time

    # 循环请求数据，直到达到结束时间
    while current_time < end_time:
        # 获取K线数据
        try:
            ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=current_time,
                                         limit=100)  # 每次请求100条数据
        except Exception as e:
            raise f"获取数据时发生错误,错误原因为: {e}"

        # 如果没有数据返回，退出循环
        if not ohlcv:
            return None

        # 将获取到的数据添加到 all_data 列表
        all_data.extend(ohlcv)

        # 更新当前时间为最后一条数据的时间戳
        current_time = ohlcv[-1][0] + 1  # 加1毫秒以避免重复请求同一数据

        # 为了避免触发API限制，可以添加延时
        time.sleep(2)  # 睡眠2秒

    # 将所有数据转换为DataFrame以便于分析
    data_frame = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data_frame['timestamp'] = pd.to_datetime(data_frame['timestamp'], unit='ms')  # 转换时间戳

    # 过滤数据，保留指定时间范围内的数据
    data_frame = data_frame[(data_frame['timestamp'] >= start_date) & (data_frame['timestamp'] < end_date)]

    return data_frame


def fetch_all_ohlcv(symbol, start_date, timeframe, exchange_name='okx'):
    """
    获取从开始时间到现在的指定交易对的所有K线数据
    :param exchange_name: 交易所名称，例如 'okx'
    :param symbol: 交易对，例如 'BTC/USDT' 或 'BTC/USDT:SWAP'
    :param start_date: 开始时间，格式为 'YYYY-MM-DD'
    :param timeframe: K线时间周期，例如 '1m', '5m', '1h', '1d'
    :return: DataFrame，包含从开始时间到现在的所有K线数据
    """
    # 创建交易所对象
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class()

    # 将开始时间转换为毫秒时间戳
    start_time = int(time.mktime(time.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000

    # 初始化一个空的 DataFrame 用于存储所有数据
    all_data = []

    # 当前时间设置为当前时间戳
    current_time = int(time.time() * 1000)

    # 循环请求数据，直到达到当前时间
    while current_time > start_time:
        # 获取K线数据
        try:
            ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=start_time,
                                         limit=100)  # 每次请求100条数据

        except Exception as e:
            raise f"获取数据时发生错误,错误原因为: {e}"

        # 如果没有数据返回，退出循环
        if not ohlcv:
            return None

        # 将获取到的数据添加到 all_data 列表
        all_data.extend(ohlcv)

        # 更新开始时间为返回数据的最后一条时间戳
        start_time = ohlcv[-1][0] + {
            '1d': 60 * 60 * 24 * 1000,
            '1h': 60 * 60 * 1000,
            '5m': 60 * 1000 * 5,
            '1m': 60 * 1000
        }.get(timeframe, 0)  # 获取返回数据的最后一条时间戳

        # 为了避免触发API限制，可以添加延时
        time.sleep(5)  # 睡眠5秒

    # 将所有数据转换为DataFrame以便于分析
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # 转换时间戳

    # 计算MA5并添加到DataFrame中
    df['ma5'] = df['close'].rolling(window=5).mean()

    return df


def save_to_mysql(host='localhost', port=3306, user='', password='', database='', table='ohlcv_data', df=None):
    """
    将DataFrame保存到MySQL数据库中
    :param host: MySQL主机地址，默认为localhost
    :param port: MySQL端口，默认为3306
    :param user: MySQL用户名
    :param password: MySQL密码
    :param database: 数据库名
    :param table: 表名
    :param df: DataFrame，包含要保存的数据
    """
    try:
        # 连接到MySQL数据库
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
        )

        with connection:
            with connection.cursor() as cursor:
                # 创建数据库（如果不存在）
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`;")
                cursor.execute(f"USE `{database}`;")

                # 创建表（如果不存在）
                cursor.execute(f"""  
                CREATE TABLE IF NOT EXISTS `{table}` (  
                    `id` INT AUTO_INCREMENT PRIMARY KEY,  
                    `datetime` DATETIME NOT NULL,  
                    `open` FLOAT,  
                    `high` FLOAT,  
                    `low` FLOAT,  
                    `close` FLOAT,  
                    `volume` FLOAT
                );  
                """)

                # 准备插入数据的SQL语句
                insert_query = f"""  
                INSERT INTO `{table}` (`datetime`, `open`, `high`, `low`, `close`, `volume`)  
                VALUES (%s, %s, %s, %s, %s, %s)  
                """

                # 将DataFrame中的数据插入到数据库
                for index, row in df.iterrows():
                    # 将timestamp列重命名为datetime列

                    data = (
                        row['timestamp'], row['open'], row['high'], row['low'], row['close'], row['volume'])
                    # 打印要插入的数据以进行检查
                    print(f"Inserting: {data}")
                    cursor.execute(insert_query, data)

                    # 提交事务
                connection.commit()
                print(f"成功将数据保存到 {database}.{table} 表中")

    except Exception as e:
        raise f"将数据保存到mysql时发生错误,错误原因为: {e}"


def fetch_all_tickers(exchange_name):
    """
    获取指定交易所所有交易对的最新市场数据。

    :param exchange_name: 交易所名称，如 'binance', 'coinbase', 等等
    :return: 交易对的最新市场数据字典
    """
    try:
        # 创建交易所实例
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class()

        # 获取所有交易对的最新市场数据
        tickers = exchange.fetch_tickers()

        return tickers
    except Exception as e:
        return None


def get_df_from_mysql(host='localhost', port=3306, user='', password='', database='', table='ohlcv_data'):
    """
    从 MySQL 数据库中获取指定表的数据并转换为 DataFrame。

    :param host: MySQL 主机地址，默认为 localhost。
    :param port: MySQL 端口，默认为 3306。
    :param user: MySQL 用户名。
    :param password: MySQL 密码。
    :param database: 数据库名。
    :param table: 表名。
    :return: DataFrame，包含从数据库中获取的数据。
    """
    try:
        # 连接到 MySQL 数据库
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )

        with connection:
            # 使用 pandas 的 read_sql 方法从数据库读取数据并转换为 DataFrame
            query = f"SELECT * FROM `{table}`;"
            df = pd.read_sql(query, connection)

            return df

    except Exception as e:
        raise f"从mysql数据库中获取数据时发生错误,错误原因为: {e}"


from myokx import get_ticker_last_price


def get_btc_sol_eth_doge_last_price_mean_normalized() -> np.array:
    """
    获取比特币（BTC）、Solana（SOL）、以太坊（ETH）和狗狗币（DOGE）的最新价格，并计算其标准化后的平均值。

    该函数首先尝试从市场获取四种加密货币的最新价格，然后计算这些价格的平均值、标准差，并进行标准化处理。
    标准化是将数据转换为具有零均值和单位标准差的过程，这有助于比较不同数据集的分布。
    最后，函数返回标准化后的平均值。

    返回:
        np.array: 标准化后的平均值。

    异常:
        Exception: 如果在获取价格或进行计算过程中发生任何异常，函数将抛出异常，并提供错误原因。

    注意:
        - 该函数依赖于外部函数get_ticker_last_price来获取每种货币的最新价格。
        - 该函数假设get_ticker_last_price函数返回两个值：货币信息，和其最新价格。
        - 该函数不处理get_ticker_last_price函数可能返回的任何异常，而是将这些异常传递给调用者。
        - 该函数假设价格数据是数值类型，可以进行数学运算。
    """
    try:
        # 从市场获取每种货币的最新价格
        btc, btc_last_price = get_ticker_last_price('BTC-USDT-SWAP')
        sol, sol_last_price = get_ticker_last_price('SOL-USDT-SWAP')
        eth, eth_last_price = get_ticker_last_price('ETH-USDT-SWAP')
        doge, doge_last_price = get_ticker_last_price('DOGE-USDT-SWAP')

        # 将价格存储在numpy数组中
        price = np.array([btc_last_price, sol_last_price, eth_last_price, doge_last_price])

        # 计算价格的平均值
        mean_price = np.mean(price)

        # 计算价格的标准差
        std = np.std(price)

        # 对价格进行标准化处理
        normalized = (price - mean_price) / std
        # 计算标准化后的平均值
        mean_normalized = np.mean(normalized)

        # 返回标准化后的平均值
        return mean_normalized
    except Exception as e:
        # 如果发生异常，抛出异常信息
        raise Exception(f"获取BTC, SOL, ETH, DOGE币种价格时发生错误, 错误原因为: {e}")
