"""
该模块定义了一个模型训练线程，用于训练和更新交易预测模型。
"""

" 内置模块 "
import time

" 自定义模块 "
from predict_model import get_data_from_mysql, data_preprocessing, divide_feature_and_target, train_model
import global_vars
from mymail import send_email


def model_train_thread(sender: str,
                       receiver: str,
                       mail_password: str,
                       host: str,
                       username: str,
                       password: str,
                       database_name: str,
                       start_date_str: str,
                       port: int = 3306):
    """
       模型训练线程，负责周期性地训练和更新交易预测模型。
       该函数在一个无限循环中运行，每次循环都会尝试从数据库中获取数据，
       预处理数据，划分特征和目标集，训练模型，并保存最好的模型对象。
       如果在任何步骤中发生异常，它会发送邮件通知并停止线程。

       参数：
       - sender: QQ邮件发送者邮箱地址，用于发送错误通知。
       - receiver: QQ邮件接收者邮箱地址，用于接收错误通知。
       - mail_password: 发送者QQ邮箱的授权码，用于邮件发送验证。
       - host: MySQL数据库主机地址。
       - username: MySQL数据库用户名。
       - password: MySQL数据库密码。
       - database_name: 要操作的数据库名称。
       - start_date_str: 用于数据提取的起始日期字符串，格式为 '%Y-%m-%d'。
       - port: MySQL数据库端口号，默认为3306。

       返回：
       - 无返回值，但会保存训练好的模型对象到全局变量 `global_vars.best_model` 中。

       异常处理：
       - 如果在数据处理或模型训练过程中发生异常，会通过 `send_email` 函数发送错误通知邮件，
         并将 `global_vars.s_finished_event` 设置为 True 以停止所有线程。
       """
    global_vars.lq.push(('模型训练线程-状态信息', 'info', '模型训练线程启动'))
    while True:

        if global_vars.s_finished_event:
            global_vars.lq.push(('模型训练线程-状态信息', 'info', '模型训练线程停止'))
            break

        try:

            # 从数据库中获取数据
            data, target = get_data_from_mysql(host=host, username=username, password=password,
                                               database_name=database_name, start_date_str=start_date_str, port=port)

            # 数据预处理
            global_vars.attr_df, all_df = data_preprocessing(data, target)

            # 如果数据量不足，不训练模型
            if len(all_df) < 1000:
                global_vars.lq.push(("模型训练线程-状态信息", "info", "交易数据量不足，不训练模型"))
                time.sleep(4 * 60)
                continue

            # 划分数据集
            train_data, test_data, train_target, test_target = divide_feature_and_target(all_df)

            # 训练模型返回最好的模型
            global_vars.best_model = train_model(train_data, train_target, test_data, test_target)
            global_vars.lq.push(("模型训练线程-状态信息", "info", "'预测模型训练完成'"))
            time.sleep(4 * 60)
        except Exception as e:
            send_email(sender=sender, receiver=receiver, password=mail_password,
                       subject='来自okx自动化策略程序的运行错误的提醒:',
                       content="发生在:model_train_thread线程。\n"
                               f"错误原因：{e}\n")
            global_vars.s_finished_event = True
            break