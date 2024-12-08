"""
包含一个PredictModel类，用于从数据库获取数据、数据预处理、划分数据集、训练模型并返回最好的模型对象。
@Time: 2024/12/8 9:45
@Author: ysh
@File: predict_model.py
"""
import pandas as pd
import pymysql
from datetime import datetime, timedelta


class PredictModel:
    def get_data_from_mysql(self, host: str = "101.34.59.205", username: str = "云服务器mysql",
                            password: str = "yshhsq31",
                            database_name: str = "eth数据库", start_date_str: str = "2024-12-05",
                            port: int = 3306) -> pd.DataFrame:
        """
        从MySQL数据库中获取数据。
        :param: host (str): MySQL数据库服务器的IP地址，默认为"101.34.59.205"。
        :param: username (str): MySQL数据库的用户名，默认为"云服务器mysql"。
        :param: password (str): MySQL数据库的密码，默认为"yshhsq31"。
        :param: database_name (str): 要连接的数据库名称，默认为"eth数据库"。
        :param: start_date_str (str): 开始日期字符串，格式为"%Y-%m-%d"，默认为"2024-12-05"。
        :param: port (int): MySQL数据库服务的端口，默认为3306。
        :return: pandas.DataFrame: 从MySQL数据库中获取的数据。
        """
        date_format = "%Y-%m-%d"
        re_df = None
        while True:
            # 修正此处，应该是datetime.strptime，拼写错误已修正
            start_date_object = datetime.strptime(start_date_str, date_format)
            table_date_name = start_date_str.replace("-", "_")
            table_name = f"{table_date_name}实时数据"
            try:
                with pymysql.connect(host=host, user=username, password=password, database=database_name,
                                     port=port) as client:
                    # 查询语句
                    try:
                        sql = f"select 当前时间,当前价格,上一次价格,上一次五个当前价格的平均值,当前五个当前价格的平均值,上一次主流货币当前价格标准化均值,当前主流货币当前价格标准化均值,上一次bidSz,当前bidSz,上一次askSz,当前askSz,上一次24小时交易量,当前24小时交易量,交易类型 from {table_name} where 交易类型 in (-1,1)"
                        temp_df = pd.read_sql(sql, con=client)
                        if re_df is None:
                            re_df = temp_df.copy()
                        else:
                            re_df = pd.concat([re_df, temp_df], axis=0, ignore_index=True)

                        next_date_object = start_date_object + timedelta(days=1)
                        next_date_str = next_date_object.strftime(date_format)
                        start_date_str = next_date_str
                    except Exception as e:
                        # 当内层try出现异常，比如没有下一个日期对应的数据表时，直接返回已经获取到的数据
                        print(f"查询数据出现异常: {e}，返回已获取的数据。")
                        return re_df
            except Exception as e:
                raise e

    def get_target_from_mysql(self, host: str = "101.34.59.205", username: str = "云服务器mysql",
                              password: str = "yshhsq31",
                              database_name: str = "eth数据库", start_date_str: str = "2024-12-05",
                              port: int = 3306) -> pd.DataFrame:
        """
        从MySQL数据库中获取目标数据。
        :param host: MySQL数据库服务器的IP地址，默认为"101.34.59.205"。
        :param username:  MySQL数据库的用户名，默认为"云服务器mysql"。
        :param password: MySQL数据库的密码，默认为"yshhsq31"。
        :param database_name: 要连接的数据库名称，默认为"eth数据库"。
        :param start_date_str: 开始日期字符串，格式为"%Y-%m-%d"，默认为"2024-12-05"。
        :param port: MySQL数据库服务的端口，默认为3306。
        :return: pandas.DataFrame: 从MySQL数据库中获取的目标数据。
        """
        date_format = "%Y-%m-%d"
        re_df = None
        while True:
            # 修正此处，应该是datetime.strptime，拼写错误已修正
            start_date_object = datetime.strptime(start_date_str, date_format)
            table_date_name = start_date_str.replace("-", "_")
            table_name = f"{table_date_name}实时数据"
            try:
                with pymysql.connect(host=host, user=username, password=password, database=database_name,
                                     port=port) as client:
                    # 查询语句
                    try:
                        sql = f"select 当前时间,交易类型 from {table_name} where 交易类型 in (-2,2,3)"
                        temp_df = pd.read_sql(sql, con=client)
                        if re_df is None:
                            re_df = temp_df.copy()
                        else:
                            re_df = pd.concat([re_df, temp_df], axis=0, ignore_index=True)

                        next_date_object = start_date_object + timedelta(days=1)
                        next_date_str = next_date_object.strftime(date_format)
                        start_date_str = next_date_str
                    except Exception as e:
                        # 当内层try出现异常，比如没有下一个日期对应的数据表时，直接返回已经获取到的数据
                        print(f"查询数据出现异常: {e}，返回已获取的数据。")
                        return re_df
            except Exception as e:
                raise e

    def data_preprocessing(self, data: pd.DataFrame, target: pd.DataFrame) -> tuple:
        """
        数据预处理函数
        :param data:  包含特征的数据集
        :param target:   包含目标变量的数据集
        :return:   返回两个dframe，一个包含没有进行标准化的特征集（attr_data，这个数据集可用在方法：data_to_df作为orignal_data的参数）；一个包含标准化的特征和目标变量合并集（all_df，这个数据集可用在方法：divide_feature_and_target作为data的参数）
        """
        if len(data) == len(target) + 1:  # 删除正在交易，还没有确定是否盈亏的记录
            # 获取索引的最后一个值（假设是整数索引）
            last_index = data.index[-1]
            # 使用drop方法删除最后一行
            data = data.drop(last_index)

        target = target.rename(columns={"交易类型": "盈亏情况"})
        # 新建特征列
        data["新周期与上一周期的价差"] = data["当前价格"] - data["上一次价格"]
        data["新周期五个当前价格的均值与上一周期五个当前价格的均值差"] = data["当前五个当前价格的平均值"] - data[
            "上一次五个当前价格的平均值"]
        data["新周期主流货币的价格均值与上一周期主流货币的价格均值差"] = data["当前主流货币当前价格标准化均值"] - data[
            "上一次主流货币当前价格标准化均值"]
        data["新周期bisSz与上一周期的bisSz差"] = data["当前bidSz"] - data["上一次bidSz"]
        data["新周期askSz与上一周期的askSz差"] = data["当前24小时交易量"] - data["上一次24小时交易量"]
        data["新周期24小时交易量与上一周期的24小时交易量差"] = data["当前24小时交易量"] - data["上一次24小时交易量"]

        # 提取特征列
        attr_data = data[["新周期与上一周期的价差", "新周期五个当前价格的均值与上一周期五个当前价格的均值差",
                          "新周期主流货币的价格均值与上一周期主流货币的价格均值差", "新周期bisSz与上一周期的bisSz差",
                          "新周期askSz与上一周期的askSz差", "新周期24小时交易量与上一周期的24小时交易量差"]]

        # 标准化
        for col in attr_data.columns:
            mean_value = attr_data[col].mean()
            std_value = attr_data[col].std()
            attr_data[col] = (attr_data[col] - mean_value) / std_value

        all_df = pd.concat([attr_data, target["盈亏情况"]], axis=1)

        all_df.loc[all_df['盈亏情况'].isin([-2, 2]), '盈亏情况'] = 1  # 1表示获利
        all_df.loc[all_df['盈亏情况'] == 3, '盈亏情况'] = 0  # 表示亏损

        return attr_data, all_df

    def divide_feature_and_target(self, data: pd.DataFrame, test_size: float = 0.2) -> tuple:
        """
        划分特征集和目标集
        :param data:  包含特征和目标的数据集
        :param test_size:  测试集占总数据的比例，默认为0.2。
        :return: 训练集特征、测试集特征、训练集目标、测试集目标。
        """
        # 划分特征集和目标集
        target = data["盈亏情况"]
        attr = data[["新周期与上一周期的价差", "新周期五个当前价格的均值与上一周期五个当前价格的均值差",
                     "新周期主流货币的价格均值与上一周期主流货币的价格均值差", "新周期bisSz与上一周期的bisSz差"
            , "新周期askSz与上一周期的askSz差", "新周期24小时交易量与上一周期的24小时交易量差"]]

        # 划分训练集和测试集
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(attr, target, test_size=test_size, random_state=42)

        return X_train, X_test, y_train, y_test

    def train_model(self, X_train: pd.DataFrame, y_train: pd.DataFrame, X_test: pd.DataFrame,
                    y_test: pd.DataFrame) -> object:
        """
        会依次训练多个模型，根据评估结果返回最好的模型对象
        :param X_train: 训练集特征
        :param y_train: 训练集目标
        :param y_test:  测试集目标
        :param X_test:  测试集特征
        :return: 评分最好的模型对象
        """
        # 训练模型
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.metrics import accuracy_score

        # 创建模型对象
        models = {"DecisionTreeClassifier": DecisionTreeClassifier(),
                  "RandomForestClassifier": RandomForestClassifier(), "KNeighborsClassifier": KNeighborsClassifier()}

        # 训练模型，返回评估结果最好的模型对象
        best_model = None
        best_score = 0
        for model_name, model in models.items():  # 训练模型
            model.fit(X_train, y_train)

            # 预测测试集
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            if accuracy > best_score:
                best_score = accuracy
                best_model = model
        return best_model


def predict(model: object, X: pd.DataFrame) -> bool:
    """
    使用训练好的模型对一条记录进行预测。
    :param model: 训练好的模型
    :param X: 待预测的记录
    :return: True表示预测为获利，False表示预测为亏损
    """
    if model.predict(X)[0] == 1:
        return True
    else:
        return False


def data_to_df(orignal_data: pd.DataFrame, current_price: float, last_price: float,
               current_five_current_data_average: float,
               before_five_current_data_average: float, current_mean_normalized: float,
               before_mean_normalized: float, current_bidSz: float, before_bidSz: float, current_askSz: float,
               before_askSz: float, current_vol24h: float, before_vol24h: float) -> pd.DataFrame:
    """
    将一条数据转换为DataFrame，并进行标准化处理。
    :param orignal_data: 原始特征集，没有进行标准化过的。
    :param current_price: 当前价格。
    :param last_price: 上一周期价格。
    :param current_five_current_data_average: 当前周期五个当前价格的均值。
    :param before_five_current_data_average: 上一周期五个当前价格的均值。
    :param current_mean_normalized: 当前周期主流货币的价格均值。
    :param before_mean_normalized: 上一周期主流货币的价格均值。
    :param current_bidSz: 当前周期bisSz。
    :param before_bidSz: 上一周期bisSz。
    :param current_askSz: 当前周期askSz。
    :param before_askSz: 上一周期askSz。
    :param current_vol24h: 当前周期24小时交易量。
    :param before_vol24h: 上一周期24小时交易量。
    :return: 转换并标准化后的数据框架的最后一行，这是最新的符合交易的数据记录。需要标准化后返回给预测方法进行预测，如果交易的话，预测盈亏情况。
    """
    # 计算差值
    data = pd.DataFrame({"新周期与上一周期的价差": [current_price - last_price],
                         "新周期五个当前价格的均值与上一周期五个当前价格的均值差": [
                             current_five_current_data_average - before_five_current_data_average],
                         "新周期主流货币的价格均值与上一周期主流货币的价格均值差": [
                             current_mean_normalized - before_mean_normalized],
                         "新周期bisSz与上一周期的bisSz差": [current_bidSz - before_bidSz],
                         "新周期askSz与上一周期的askSz差": [current_askSz - before_askSz],
                         "新周期24小时交易量与上一周期的24小时交易量差": [current_vol24h - before_vol24h]})
    # 将数据添加到DataFrame中
    all_df = pd.concat([orignal_data, data], ignore_index=True)

    # 标准化
    for col in all_df.columns:
        mean_value = all_df[col].mean()
        std_value = all_df[col].std()
        all_df[col] = (all_df[col] - mean_value) / std_value

    return all_df.iloc[-1]
