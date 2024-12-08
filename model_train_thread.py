"""
定义了一个线程用于训练模型，每天训练一次模型，并在出现错误时发送邮件通知。
@Time: 2024/12/8 9:45
@Author: ysh
@File: model_train_thread.py
"""

import time

from predict_model import PredictModel
import global_vars
from mymail import send_email


def model_train_thread(sender: str, receiver: str, mail_password: str, host: str = "101.34.59.205",
                       username: str = "云服务器mysql",
                       password: str = "yshhsq31",
                       database_name: str = "eth数据库", start_date_str: str = "2024-12-05", port: int = 3306):
    while True:

        if global_vars.s_finished_event:
            break

        try:
            model = PredictModel()  # 创建模型对象

            # 从数据库中获取数据
            data = model.get_data_from_mysql(host, username, password, database_name, start_date_str, port)
            target = model.get_target_from_mysql(host, username, password, database_name, start_date_str, port)

            # 数据预处理
            global_vars.attr_df, all_df = model.data_preprocessing(data, target)

            # 划分数据集
            train_data, test_data, train_target, test_target = model.divide_feature_and_target(all_df)

            # 训练模型返回最好的模型
            global_vars.best_model = model.train_model(train_data, train_target, test_data, test_target)
            time.sleep(60 * 60 * 24)  # 每天训练一次模型

            print('预测模型训练完成')
        except Exception as e:
            send_email(sender=sender, receiver=receiver, password=mail_password,
                       subject='来自okx自动化策略程序的运行错误的提醒:',
                       content="发生在:model_train_thread线程。\n"
                               f"错误原因：{e}\n")
            global_vars.s_finished_event = True
            break
