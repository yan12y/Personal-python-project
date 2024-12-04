"""
这个模块是交易核心：包括交易管理，日志管理，实时数据管理
"""

" 内置模块："
import datetime
import json
import logging
import random
import sys
import threading
import time
from datetime import datetime as dt
from datetime import timedelta
from threading import Thread

" 第三方模块 "
import pymysql
import pandas as pd

" 自定义模块："
from mysqldata import get_late_date_prices, sava_all_data_to_mysql, real_time_data, create_control_program_switch_table
from myokx import MyOkx, get_ticker_last_price
from logs import LogQueue, create_log_table, log_to_mysql
from mymail import send_email
from strategy import go_long_signal, go_short_signal
from getdata import get_btc_sol_eth_doge_last_price_mean_normalized

" 全局变量声明： "
# 设置基本的日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 创建一个事件对象:当这个事件被触发，则会触发线程的结束
s_finished_event = threading.Event()

# 引入全局的退出标志变量,控制程序是否退出，当为True时，程序会退出
should_exit: bool = False

# 这个是日志队列，可以共享日志信息给日志管理线程，让日志管理线程将日志信息上传至数据库中。
lq: LogQueue = LogQueue()

# 这个是实时数据队列，存储的是实时数据，当有新的数据时，会通过队列的方式，发送给策略管理线程，由策略管理线程来处理上传到数据库中。
r_d = []  # 这个是实时数据队列，

# 日志表名，strategy_manager_thread会根据不同日期创建不同日期的日志表
log_table_name: str

# 实时数据表名，strategy_manager_thread会根据不同日期创建不同日期的实时数据表名
data_table_name: str

# 前五个当前交易对的实时价格数据
top_five_current_data = []

# 记录交易类型，0表示无交易，1表示开多，-1表示开空，2表示止盈平多，-2表示止盈平空，3表示止损
trade_type: int = 0


def strategy_manager_thread(mysql_host: str, mysql_username: str, mysql_password: str, mysql_coin_database: str,
                            mysql_coin_day_date_table: str,
                            okx_api_key: str, okx_secret_key: str, okx_passphrase: str, instId: str, leverage: int,
                            sender: str, receiver: str, sender_password: str,
                            sz: int,
                            place_position_nums: int = 150,
                            place_uplimit: float = 0.0055,
                            place_downlimit: float = 0.0015,
                            mysql_port: int = 3306,
                            l_s1: float = 0.01,
                            l_s2: float = 0.025,
                            l_s3: float = 0.045,
                            l_s4: float = 0.075,

                            l_e1: float = 0.015,
                            l_e2: float = 0.035,
                            l_e3: float = 0.065,
                            l_e4: float = 0.1,

                            s_s1: float = -0.015,
                            s_s2: float = -0.035,
                            s_s3: float = -0.065,
                            s_s4: float = -0.1,

                            s_e1: float = -0.01,
                            s_e2: float = -0.025,
                            s_e3: float = -0.045,
                            s_e4: float = -0.075,

                            l_c_limit: int = 10,
                            s_c_limit: int = 10,
                            limit_uplRatio: float = -0.5
                            ):
    """
     这是交易策略管理线程。
    注意：使用这个策略之前，请你确保mysql_username用户拥有 create,select,insert 权限
    同时，确保网络连接，vpn连接。
    :param mysql_host: 数据库主机，例如：'192.168.1.1'或者‘localhost’
    :param mysql_port: 数据库端口号，默认是：3306
    :param mysql_username: 数据库用户名（注意，这个用户必须拥有 create,select,insert 权限）
    :param mysql_password: 通行密码
    :param mysql_coin_database: 保存coin（币信息）的数据库名
    :param mysql_coin_day_date_table: 保存coin日数据的表名
    :param okx_api_key: okx申请api接口时，获得的api_key
    :param okx_secret_key: okx申请api接口时，获得的secret_key
    :param okx_passphrase: okx申请api时自己设置的密码
    :param instId: 交易类型，例如：'ETH-USDT-SWAP'
    :param leverage: 交易的杠杆倍数
    :param sender: QQ邮件发送者
    :param sz: minsSz的整数倍数
    :param receiver: QQ邮件接收者
    :param sender_password: QQ邮件发送者的密码（授权码）
    :param place_position_nums: 计划持仓时，拥有的最大头寸数量，默认为150
    :param place_uplimit: 涨跌上限（默认为0.45%），不会在整个程序运行过程中发生任何变化
    :param place_downlimit: 涨跌下限（默认为0.15%），不会在整个程序运行过程中发生任何变化
    :param l_s1: 这是区间u_p_1的左限，表示涨幅区间1的下限
    :param l_s2: 这是区间u_p_2的左限，表示涨幅区间2的下限
    :param l_s3: 这是区间u_p_3的左限，表示涨幅区间3的下限
    :param l_s4: 这是区间u_p_4的左限，表示涨幅区间4的下限
    :param l_e1: 这是区间u_p_1的右限，表示涨幅区间2的上限
    :param l_e2: 这是区间u_p_2的右限，表示涨幅区间3的上限
    :param l_e3: 这是区间u_p_3的右限，表示涨幅区间4的上限
    :param l_e4:  这是区间u_p_4的右限，表示涨幅区间4的上限
    :param s_s1: 这是区间d_p_1的左限，表示跌幅区间1的下限
    :param s_s2: 这是区间d_p_2的左限，表示跌幅区间2的下限
    :param s_s3: 这是区间d_p_3的左限，表示跌幅区间3的下限
    :param s_s4: 这是区间d_p_4的左限，表示跌幅区间4的下限
    :param s_e1: 这是区间d_p_2的右限，表示跌幅区间1的上限
    :param s_e2: 这是区间d_p_3的右限，表示跌幅区间2的上限
    :param s_e3: 这是区间d_p_4的右限，表示跌幅区间3的上限
    :param s_e4: 这是区间d_p_4的右限，表示跌幅区间4的上限
    :param l_c_limit: 这是最多的开多仓次数
    :param s_c_limit: 这是最多的开空仓次数
    :param limit_uplRatio: 为实现收益额 / 保证金（止损最大比值）
    :return: 无返回值，此线程函数负责执行交易策略并管理相关操作。
    """

    global s_finished_event
    global log_table_name
    global lq
    global data_table_name
    global r_d
    global should_exit
    global top_five_current_data
    global trade_type
    ppn = place_position_nums # 计划持仓时，实际拥有的最大头寸数量

    lq.push(('程序状态', 'Info', '程序开始启动'))

    before_mean_normalized: float = 0  # 上一次btc,sol,eth,doge的实时价格标准化均值
    before_five_current_data_average = 0  # 上一次五个当前交易对的实时价格的平均值
    current_five_current_data_average = 0  # 当前五个当前交易对的实时价格的平均值

    before_bidSz: float = 0 # 上一次买入量
    before_askSz: float = 0 # 上一次卖出量
    before_vol24h: float = 0 # 上一次24小时成交量

    last_p_p: float = 0  # 当前价格与上一次价格变化百分比

    # 设置随机时间区间，随机休眠的时间会从这个区间内生成。
    random_start = 10  # 随机时间的左区间
    random_end = 20  # 随机时间的右区间

    last_p = 0  # 上一次循环的价格

    # 实例化MyOkx实例
    o = MyOkx(okx_api_key, okx_secret_key, okx_passphrase)

    # 从配置文件中加载下列参数:
    (long_place_downlimit, long_place_uplimit, short_place_downlimit, short_place_uplimit,
     l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4, n_sz) = load_parameter()

    # 生成的随机时间,由random.randint(random_start, random_end)生成，初始化为0
    random_time:int =0

    # 昨日收盘价格，初始为0
    last_date_price: float = 0

    # 创建控制程序开关的表
    while True:
        try:
            create_control_program_switch_table(host=mysql_host, username=mysql_username, password=mysql_password,
                                                database=mysql_coin_database, table='switch')
            lq.push(('创建控制程序开关表', 'Success', '创建成功'))
            print('创建控制程序开关表成功')
            break
        except Exception as e:
            print(f'创建控制程序开关表失败:{e}，正在重试...')
            lq.push(('创建控制程序开关表', 'Error', '创建失败'))
            time.sleep(3)

    today = datetime.datetime.now().strftime('%Y-%m-%d')  # today是当前时间
    today_obj = dt.strptime(today, "%Y-%m-%d")  # 将字符串转换为时间对象
    yesterday_obj = today_obj - timedelta(days=1)  # 昨天的时间对象
    yesterday = yesterday_obj.strftime("%Y-%m-%d")  # 昨天的时间字符串
    data_table_name = today.replace('-', '_') + '实时数据'

    c = 0  # 重试计数器
    while True:

        if should_exit is True or s_finished_event.is_set():
            # 及时保存重要参数
            try:
                save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit, short_place_uplimit,
                               l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4,n_sz)
                lq.push(('参数保存', 'Info', '正在保存重要参数'))
            except:
                lq.push(('参数保存', 'Error', '保存重要参数失败'))
            finally:
                lq.push(('程序状态', 'Info', '程序成功退出'))
                break

        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            " 新的一天更新逻辑 "
            if today != yesterday:

                # 等待队列清空
                if lq != [] or r_d != []:
                    time.sleep(3)

                data_table_name = today.replace('-', '_') + '实时数据'  # 创建用于存储新的一天的实时数据的新表名

                today_str = today.replace('-', '_')
                log_table = f'{today_str}_{leverage}X_logs'  # 创建用于存储新的一天的日志数据的新表名
                log_table_name = log_table

                # 在数据库中创建日志表
                if create_log_table(mysql_host=mysql_host, mysql_port=mysql_port, mysql_username=mysql_username,
                                    mysql_password=mysql_password,
                                    mysql_database=mysql_coin_database, mysql_log_table=log_table):
                    lq.push(('创建日志表', 'Success', '创建新日期的日志表'))
                else:
                    # 尝试发送邮件通知后，保存参数到配置文件，再停止程序
                    s_finished_event.set()  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止
                    send_email(sender=sender, receiver=receiver, password=sender_password,
                               subject='来自okx自动化策略程序的运行错误的提醒:',
                               content="线程：strategy_manager_thread"
                                       "\n创建新的日志表失败,退出程序"
                                       "\n请你前往服务器检查服务器网络,"
                               )
                    should_exit = True
                    save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit,
                                   short_place_uplimit,
                                   l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4,n_sz)
                    continue

                yesterday_obj = dt.strptime(yesterday, "%Y-%m-%d")  # 将字符串转换为时间对象
                yesterday_and_yesterday_obj = yesterday_obj - timedelta(days=1)  # 前一天的时间对象
                yesterday_and_yesterday = yesterday_and_yesterday_obj.strftime("%Y-%m-%d")

                # 保存前一天的日数据到数据库中去
                a = 0  # 重试计数器
                while True:
                    try:
                        sava_all_data_to_mysql(yesterday_and_yesterday, instId, username=mysql_username,
                                               password=mysql_password,
                                               host=mysql_host, database=mysql_coin_database, port=mysql_port,
                                               table=mysql_coin_day_date_table)  # 保存前一天的日数据到数据库中去

                        lq.push(('保存前一天的收盘价', 'Success', f'保存前一天收盘价到数据库成功'))
                        break
                    except Exception as e:
                        if a < 3:
                            lq.push(('保存前一天的收盘价', 'Error', f'保存前一天收盘价到数据库失败:{e},5秒后重试'))
                            a += 1
                            time.sleep(5)
                        else:
                            # 多次保存前一天的数据失败
                            s_finished_event.set()  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止
                            should_exit = True # 退出标志设置为True
                            send_email(sender=sender, receiver=receiver, password=sender_password,
                                       subject='来自okx自动化策略程序的运行错误的提醒:',
                                       content="发生在:strategy_manager_thread线程。\n"
                                               "错误位置：将前一天的日数据保存到数据库中时失败。\n"
                                               f"错误原因：{e}\n")
                            save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit,
                                           short_place_uplimit,
                                           l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4,n_sz)
                            break
                if should_exit is True: continue  # 保存前一天的日数据到数据库中去失败，应该退出程序,否则继续执行

                yesterday = today  # 更新前一天
                # 从数据库中重新获取前一天的收盘价
                b = 0  # 重试计数器
                while True:
                    try:
                        last_date_price = get_late_date_prices(username=mysql_username, password=mysql_password,
                                                               host=mysql_host, database=mysql_coin_database,
                                                               table=mysql_coin_day_date_table)
                        lq.push(('获取前一天的收盘价', 'Success', f'获取前一天收盘价成功'))
                        break
                    except Exception as e:
                        if b < 3:
                            lq.push(('获取前一天的收盘价', 'Error', f'获取前一天数据失败:{e},5秒后重试'))
                            b += 1
                            time.sleep(5)
                        else:

                            # 多次获取前一天的数据失败
                            s_finished_event.set()  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止
                            should_exit = True
                            # 尝试发送邮件通知后，保存参数到配置文件，再停止程序
                            send_email(sender=sender, receiver=receiver, password=sender_password,
                                       subject='来自okx自动化策略程序的运行错误的提醒:',
                                       content="发生在：strategy_manager_thread线程。\n"
                                               "错误位置：从数据库中获取前一天数据时失败。\n"
                                               f"错误原因：{e}")

                            # 保存参数到配置文件，直接退出程序
                            save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit,
                                           short_place_uplimit,
                                           l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4,n_sz)
                            break
                if should_exit is True: continue  # 从数据库中重新获取前一天的收盘价失败，应该退出程序，否则继续执行

                # 新的一天，初始化一些参数：包括：
                # 各个u_p和d_p用于记录涨跌幅分别在某一个区间的次数。初始为0
                # random_start和random_end用于记录随机时间区间。random_start和random_end初始为10和20
                # long_place_uplimit和long_place_downlimit。开多仓的区间上下限
                # short_place_uplimit和short_place_downlimit。开空仓的区间上下限
                # l_c和s_c用于记录交易多头还是空头的次数。初始为0
                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start, random_end,
                 long_place_uplimit,
                 long_place_downlimit, short_place_uplimit, short_place_downlimit, l_c, s_c) = init_arguments(
                    place_uplimit=place_uplimit,
                    place_downlimit=place_downlimit)
                random_time = random.randint(random_start, random_end)

            " 交易前准备 "
            current_coin_data, current_price = get_ticker_last_price(instId)  # 获取当前交易类型的信息，当前价格
            current_bidSz, current_askSz = current_coin_data["bidSz"], current_coin_data["askSz"]
            current_vol24h = current_coin_data['vol24h']

            current_mean_normalized = get_btc_sol_eth_doge_last_price_mean_normalized()  # 获取BTC,SOL,ETH,DOGE的最新价格标准化的平均值

            now = datetime.datetime.now()  # 获取此时的时间
            # 格式化日期和时间
            formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

            current_positions = o.get_positions()  # 获取所有仓位信息

            current_position_nums = 0  # 当前instId类型的仓位头寸，初始化为0
            if current_positions:
                # 检查所有仓位信息中有没有 ETH-USDT-SWAP的仓位
                for position in current_positions:
                    if position["instId"] == instId:
                        pos = float(position["pos"])
                        if pos < 0:  # 说明是空头仓位
                            current_position_nums = float(position["notionalUsd"])
                            current_position_nums = -current_position_nums
                            break
                        elif pos > 0:  # 说明是多头仓位
                            current_position_nums = float(position["notionalUsd"])
                            break
                            # 注意：运行到这里，current_position_nums可正，可负的。正表示是多头仓位的头寸，负表示是空头仓位头寸

            p = (current_price - last_date_price) / last_date_price  # 这是昨天收盘价和当前价格的百分比变化

            if last_p != 0:  # 避免第一次运行，导致last_p为0
                last_p_p = (current_price - last_p) / last_p  # 当前价格和上一次价格的百分比变化

            # last_p_p ,p这个参数对整个交易逻辑和获利逻辑有着非常大的关系，同时它会影响u_p和d_p的变化。

            # 根据p值来更新u_p_1,d_p_1,u_p_2,d_p_2,u_p_3,d_p_3,u_p_4,d_p_4
            u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4 = update_u_p_and_d_p(u_p_1, d_p_1, u_p_2, d_p_2,
                                                                                        u_p_3, d_p_3, u_p_4, d_p_4,
                                                                                        p, l_s1, l_s2,
                                                                                        l_s3, l_s4, l_e1, l_e2, l_e3,
                                                                                        l_e4, s_s1, s_s2, s_s3, s_s4
                                                                                        , s_e1, s_e2, s_e3, s_e4)
            if len(top_five_current_data) < 5:
                top_five_current_data.append(current_price)
            if len(top_five_current_data) == 5:
                current_five_current_data_average = sum(top_five_current_data) / 5
                top_five_current_data.pop(0)
                top_five_current_data.append(current_price)

            " 开仓逻辑和盈利逻辑 "
            " 开多仓逻辑 "
            if go_long_signal(long_place_downlimit, long_place_uplimit, p, last_p_p, before_five_current_data_average,
                              current_five_current_data_average, before_mean_normalized, current_mean_normalized,
                              l_c, l_c_limit, before_bidSz, current_bidSz, before_vol24h, current_vol24h):

                if current_position_nums > 0 and abs(current_position_nums) >= ppn - 10:
                    lq.push(('状态更新', 'Info',
                             f'当前价格{current_price}在开多仓的区间内，但已经有多仓大于等于{ppn - 10}USDT的仓位存在！不开仓'))

                elif current_position_nums > 0 and abs(current_position_nums) < ppn - 10:  # 说明当前有多头仓位，但是小于ppn-10

                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='buy', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'买入失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'买入成功'))

                        l_c += 1  # 开多仓计数器加一

                        # 开多仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if l_c >= 3:
                            long_place_downlimit, long_place_uplimit = (
                                update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(
                                    long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, l_c=l_c))

                        #  如果交易成功，减小下一次如果发生空仓交易的触发下限和上限。因为如果下一次反转时，开反仓区间靠近，可以减小损失。
                        short_place_downlimit, short_place_uplimit = (
                            update_short_place_uplimit_and_short_place_downlimit(
                                short_place_downlimit=short_place_downlimit, short_place_uplimit=short_place_uplimit,
                                last_p=last_p, current_price=current_price,
                                place_downlimit=place_downlimit, place_uplimit=place_uplimit))
                        trade_type = 1

                elif current_position_nums < 0:  # 说明是空头仓位，开多头仓位且保证头寸小于等于ppn

                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='buy', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'买入失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'买入成功'))

                        l_c += 1  # 开多仓计数器加一

                        # 开空仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if l_c >= 3:
                            long_place_downlimit, long_place_uplimit = (
                                update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(
                                    long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, l_c=l_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        short_place_downlimit, short_place_uplimit = (
                            update_short_place_uplimit_and_short_place_downlimit(
                                short_place_downlimit=short_place_downlimit, short_place_uplimit=short_place_uplimit,
                                last_p=last_p, current_price=current_price,
                                place_downlimit=place_downlimit, place_uplimit=place_uplimit))
                        trade_type = 1

                elif current_position_nums == 0:  # 说明是无仓位，直接开多头仓位

                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='buy', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'买入失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'买入成功'))

                        l_c += 1  # 开多仓计数器加一

                        # 开多仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if l_c >= 3:
                            long_place_downlimit, long_place_uplimit = (
                                update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(
                                    long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, l_c=l_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        short_place_downlimit, short_place_uplimit = (
                            update_short_place_uplimit_and_short_place_downlimit(
                                short_place_downlimit=short_place_downlimit, short_place_uplimit=short_place_uplimit,
                                last_p=last_p, current_price=current_price,
                                place_downlimit=place_downlimit, place_uplimit=place_uplimit))
                        trade_type = 1

            # 这是开空仓的逻辑
            elif go_short_signal(short_place_downlimit, short_place_uplimit, p, last_p_p,
                                 before_five_current_data_average,
                                 current_five_current_data_average, before_mean_normalized, current_mean_normalized,
                                 s_c, s_c_limit, before_askSz, current_askSz, before_vol24h, current_vol24h):

                if current_position_nums < 0 and abs(current_position_nums) >= ppn - 10:
                    lq.push(('状态更新', 'Info',
                             f'当前价格{current_price}在开空仓的区间内，但当前已经有空仓大于等于{ppn - 10}USDT的仓位存在！不开仓'))

                elif current_position_nums > 0:  # 说明当前持有多头仓位，但需要开空空头仓位，并且保证头寸小于等于ppn

                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='sell', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'卖出失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'卖出成功'))

                        s_c += 1  # 开多仓计数器加一

                        # 开空仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if s_c >= 3:
                            short_place_downlimit, short_place_uplimit = (
                                update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(
                                    short_place_downlimit=short_place_downlimit,
                                    short_place_uplimit=short_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, s_c=s_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        long_place_downlimit, long_place_uplimit = update_long_place_uplimit_and_long_place_downlimit(
                            long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                            last_p=last_p, current_price=current_price,
                            place_downlimit=place_downlimit, place_uplimit=place_uplimit)
                        trade_type = -1

                elif current_position_nums < 0 and abs(current_position_nums) < ppn - 10:  # 说明是空头仓位，开空头仓位且保证头寸小于=150。

                    d,Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='sell', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'卖出失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'卖出成功'))

                        s_c += 1  # 开多仓计数器加一

                        # 开空仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if s_c >= 3:
                            short_place_downlimit, short_place_uplimit = (
                                update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(
                                    short_place_downlimit=short_place_downlimit,
                                    short_place_uplimit=short_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, s_c=s_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        long_place_downlimit, long_place_uplimit = update_long_place_uplimit_and_long_place_downlimit(
                            long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                            last_p=last_p, current_price=current_price,
                            place_downlimit=place_downlimit, place_uplimit=place_uplimit)
                        trade_type = -1

                elif current_position_nums == 0:  # 说明是无仓位，直接开空头仓位,而且只开100的头寸

                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='sell', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        lq.push(('交易记录', 'Error', f'卖出失败'))
                    else:
                        lq.push(('交易记录', 'Success', f'卖出成功'))

                        s_c += 1  # 开多仓计数器加一

                        # 开空仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if s_c >= 3:
                            short_place_downlimit, short_place_uplimit = (
                                update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(
                                    short_place_downlimit=short_place_downlimit,
                                    short_place_uplimit=short_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, s_c=s_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        long_place_downlimit, long_place_uplimit = update_long_place_uplimit_and_long_place_downlimit(
                            long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                            last_p=last_p, current_price=current_price,
                            place_downlimit=place_downlimit, place_uplimit=place_uplimit)
                        trade_type = -1

            # 这是仓位获利逻辑。
            elif p > 0.012 or p < - 0.012:

                today_positions = o.get_positions()  # 获取所有仓位信息
                # 获得instId类型的仓位信息
                for position in today_positions:
                    if position["instId"] == instId:
                        today_pos = float(position["pos"])

                        # 如果涨幅超过0.25 或者 跌幅超过0.25，那么就止盈
                        if p > 0.25 or p < -0.25:
                            while True:

                                if today_pos > 0:  # 多仓获利，对应(current_price-last_date_price) /last_date_price > 0.05的情况
                                    trade_type = 2
                                    re = take_progit(o=o, instId=instId, leverage=leverage, place_uplimit=place_uplimit,
                                                     place_downlimit=place_downlimit)
                                    if re:
                                        (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                         random_end,
                                         long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                         short_place_downlimit,
                                         l_c, s_c) = re
                                        ppn = place_position_nums
                                        n_sz = sz
                                        lq.push(('止盈记录', 'Success', '止盈【多,超0.25方向】成功'))
                                        break
                                    else:
                                        lq.push(('止盈记录', 'Error', '止盈【多,超0.25方向】失败'))

                                elif today_pos < 0:  # 空仓获利，对应(current_price-last_date_price) /last_date_price <
                                    # -0.05的情况
                                    trade_type = -2
                                    re = take_progit(o=o, instId=instId, leverage=leverage, place_uplimit=place_uplimit,
                                                     place_downlimit=place_downlimit)
                                    if re:
                                        (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                         random_end,
                                         long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                         short_place_downlimit,
                                         l_c, s_c) = re
                                        ppn = place_position_nums
                                        n_sz = sz
                                        lq.push(('止盈记录', 'Success', '止盈【空,超0.25方向】成功'))
                                        break
                                    else:
                                        lq.push(('止盈记录', 'Error', '止盈【空,超0.25方向】失败'))

                        # 如果u_p_1,到u_p_4其中一个大于设定值，且持有多仓，那么就平多仓
                        elif (u_p_1 > 20 and today_pos > 0) or (u_p_2 > 27 and today_pos > 0) or (
                                u_p_3 > 40 and today_pos > 0) or (u_p_4 > 6 and today_pos > 0):
                            trade_type = 2
                            re = take_progit(o=o, instId=instId, leverage=leverage, place_uplimit=place_uplimit,
                                             place_downlimit=place_downlimit)
                            if re:
                                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                 random_end,
                                 long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                 short_place_downlimit,
                                 l_c, s_c) = re
                                ppn = place_position_nums
                                n_sz = sz
                                lq.push(('止盈记录', 'Success', '止盈【多,区间计数器触发】成功'))
                            else:
                                lq.push(('止盈记录', 'Error', '止盈【多,区间计数器触发】失败'))

                        # 如果d_p_1,到d_p_4其中一个大于设定值，且持有空仓，那么就平空仓。
                        elif (d_p_1 > 10 and today_pos < 0) or (d_p_2 > 13 and today_pos < 0) or (
                                d_p_3 > 20 and today_pos < 0) or (d_p_4 > 3 and today_pos < 0):
                            trade_type = -2
                            re = take_progit(o=o, instId=instId, leverage=leverage, place_uplimit=place_uplimit,
                                             place_downlimit=place_downlimit)
                            if re:
                                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                 random_end,
                                 long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                 short_place_downlimit,
                                 l_c, s_c) = re
                                ppn = place_position_nums
                                n_sz = sz
                                lq.push(('止盈记录', 'Success', '止盈【空,区间计数器触发】成功'))
                            else:
                                lq.push(('止盈记录', 'Error', '止盈【空,区间计数器触发】失败'))
                        else:
                            lq.push(('状态更新', 'Info', '当前价格符合获利价格区间但是没有触发条件'))
                            break  # 跳出获利逻辑的for循环

                    lq.push(('状态更新', 'Info', f'当前没有持有{instId}类型的仓位'))

            # 当任何条件都不满足，就休息一段时间，避免频繁请求。
            else:
                lq.push(('状态更新', 'Info', '当前价格不符合开仓条件,也不符合获利条件'))

            # 如果是亏损状态，下面方法会自动判断是否符合止损条件，然后一键平仓
            close_positions_re = o.close_positions(instId=instId, leverage=leverage, ordType='market', tdMode='cross',
                                                   limit_uplRatio=limit_uplRatio)

            if close_positions_re:
                if close_positions_re == 1:
                    trade_type = 3
                    # 止损后，如果下一次开仓加倍
                    n_sz += 1
                    ppn = ppn + 25 
                    lq.push(('止损记录', 'Success', '一键止损成功'))
                else:
                    lq.push(('止损记录', 'Error', '一键止损失败'))

            # 整理需要更新到数据库的数据
            # 格式化列表 d
            d = [
                formatted_now,  # 当前时间
                current_price,  # 当前价格
                last_p,  # 上一次价格
                p,  # 较昨天的涨跌幅
                last_p_p,  # 上一次价格和前一次价格的涨跌幅
                before_five_current_data_average,  # 上一次五个当前价格的平均值
                current_five_current_data_average,  # 当前五个当前价格的平均值
                before_mean_normalized,  # 上一次主流币当前价格标准化平均值
                current_mean_normalized,  # 当前主流币当前价格的平均值
                before_bidSz,  # 上一次bidSz
                current_bidSz,  # 当前bidSz
                before_askSz,  # 上一次askSz
                current_askSz,  # 当前askSz
                before_vol24h,  # 上一次24小时交易量
                current_vol24h,  # 当前24小时交易量
                l_c,  # 开多计数
                s_c,  # 开空计数
                random_time,  # 下一次休眠时间
                u_p_1,  # 多仓涨幅区间1次数
                u_p_2,  # 多仓涨幅区间2次数
                u_p_3,  # 多仓涨幅区间3次数
                u_p_4,  # 多仓涨幅区间4次数
                d_p_1,  # 空仓跌幅区间1次数
                d_p_2,  # 空仓跌幅区间2次数
                d_p_3,  # 空仓跌幅区间3次数
                d_p_4,  # 空仓跌幅区间4次数
                long_place_downlimit,  # 多仓开仓下限
                long_place_uplimit,  # 多仓开仓上限
                short_place_downlimit,  # 空仓开仓下限
                short_place_uplimit,  # 空仓开仓上限
                current_position_nums,  # 当前仓位数量
                trade_type  # 交易类型
            ]

            r_d.append(d)

            # 更新上次前五个的当前价格平均值为当前前五个的当前价格平均值
            before_five_current_data_average = current_five_current_data_average
            # before_bidSz为当前bidSz,跟新before_askSz为当前askSz
            before_bidSz, before_askSz = current_bidSz, current_askSz
            # 更新上一次24小时交易量
            before_vol24h = current_vol24h
            # 更新上一次btc,sol,eth,doge的价格标准化均值
            before_mean_normalized = current_mean_normalized

            time.sleep(random_time)  # 休息一段时间
            # 更新随机休眠时间和上一次循环的价格，用于下次循环
            random_start, random_end = modulate_randomtime(random_start, random_end, last_p, current_price)
            random_time = random.randint(random_start, random_end)  # 更新下一次随机休眠时间
            last_p = current_price  # 更新上一次循环的价格，这参数必须一次循环更新一次

            trade_type = 0  # 初始化交易类型
            # 刷新标准输出缓冲区，使其立即显示在控制台
            sys.stdout.flush()


        except Exception as e:
            if c < 3:
                lq.push(('错误记录', 'Error', f'出现异常错误: {e}，将重试'))
                c += 1
                time.sleep(10)  # 休眠10秒后重试

            else:  # 多次重新执行失败，发送邮件通知，退出程序，等待下一次计划程序的启动
                s_finished_event.set()  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止
                should_exit = True
                send_email(sender=sender, receiver=receiver, password=sender_password,
                           subject='来自okx自动化策略程序的运行错误的提醒:',
                           content="发生在:strategy_manager_thread线程。\n"
                                   "错误位置：主while第一个try。\n"
                                   f"错误原因：{e}\n")
                # 及时保存重要参数
                save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit, short_place_uplimit,
                               l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4,n_sz)



def modulate_randomtime(random_start: int, random_end: int, last_p: float, current_price):
    """
    此函数用于根据市场价格变动调整随机休眠时间区间。

    该函数根据上一次循环的价格（last_p）与当前价格（current_price）的比较结果来调整随机休眠时间的区间（random_start 和 random_end）。这个调整是基于价格变动的百分比（last_p_p），以此来反映市场波动性，并决定下一次循环的休眠时间，从而减少在高波动期间的交易频率，或在低波动期间增加交易机会。

    :param random_start: 随机休眠时间区间的左区间，表示休眠时间的最小值。
    :param random_end: 随机休眠时间区间的右区间，表示休眠时间的最大值。
    :param last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    :param current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。
    :return: 调整后的随机休眠时间区间（random_start, random_end）。
    """
    if last_p == 0:  # 如果last_p为0，则不进行任何操作（因为last_p下面将作为作为除数，除数不能为零。）
        return random_start, random_end

    last_p_p = abs((last_p - current_price) / last_p)

    if last_p_p >= 0.01:  # 变化太快
        random_start = 2
        random_end = 4
        return random_start, random_end

    elif 0.001 < last_p_p < 0.0015:
        random_start, random_end = random_start - 20, random_end - 45

    elif 0.0015 < last_p_p:
        random_start, random_end = random_start - 45, random_end - 70  # 随机时间区间缩小，且调整程度很大

    elif 0.0005 < last_p_p < 0.001:
        random_start, random_end = random_start + 1, random_end + 5

    elif last_p_p < 0.0005:
        random_start, random_end = random_start + 5, random_end + 20

    # 超出范围则调整，不超出直接使用
    if random_start < 2:
        random_start = 2
    elif random_start > 45:
        random_start = 45

    if random_end < 4:
        random_end = 4
    elif random_end > 100:
        random_end = 100

    if random_end < random_start:
        t = random_start
        random_start = random_end
        random_end = t

    return random_start, random_end


def init_arguments(place_uplimit, place_downlimit):
    """
    此函数用于初始化交易策略中使用的一系列动态参数。

    这些参数包括记录不同价格变动区间的次数计数器、随机时间区间的界限、开仓的上下限等。这些参数对于确定交易策略的行为至关重要，比如决定何时开仓、何时平仓等。

    :param place_uplimit: 用户设定的开仓涨幅上限，用于初始化开多仓和开空仓的上限。
    :param place_downlimit: 用户设定的开仓跌幅下限，用于初始化开多仓和开空仓的下限。
    :return: 一系列初始化后的参数，包括：
        u_p_1, d_p_1: 分别记录涨幅和跌幅在特定区间1的次数。
        u_p_2, d_p_2: 分别记录涨幅和跌幅在特定区间2的次数。
        u_p_3, d_p_3: 分别记录涨幅和跌幅在特定区间3的次数。
        u_p_4, d_p_4: 分别记录涨幅和跌幅在特定区间4的次数。
        random_start, random_end: 随机时间区间的左右界限。
        long_place_uplimit, long_place_downlimit: 开多仓的涨幅上下限。
        short_place_uplimit, short_place_downlimit: 开空仓的跌幅上下限。
        l_c, s_c: 开多仓和开空仓的次数计数器。
        """
    # 如果获利平掉所有仓位后，有一些动态参数需要初始化
    u_p_1 = 0  # 涨幅（0.015  -  0.05）次数
    d_p_1 = 0  # 跌幅（-0.015  -  -0.05）次数

    u_p_2 = 0
    d_p_2 = 0

    u_p_3 = 0
    d_p_3 = 0

    u_p_4 = 0
    d_p_4 = 0

    random_start = 10  # 变化时不能越过（5-30）之间。
    random_end = 20  # 变化时不能越过（10-40）之间。

    long_place_uplimit = place_uplimit  # 多仓的上限涨幅率
    long_place_downlimit = place_downlimit
    short_place_uplimit = place_uplimit
    short_place_downlimit = place_downlimit

    l_c = 0  # 开多仓的计数器
    s_c = 0  # 开空仓的计数器

    return (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start, random_end, long_place_uplimit,
            long_place_downlimit, short_place_uplimit, short_place_downlimit, l_c, s_c)


def update_u_p_and_d_p(u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, p, l_s1, l_s2,
                       l_s3, l_s4, l_e1, l_e2, l_e3, l_e4, s_s1, s_s2, s_s3, s_s4, s_e1, s_e2, s_e3, s_e4):
    """
    此函数用于根据当前价格变动更新不同价格变动区间的计数器。

    该函数根据当前的价格变动百分比（p），更新记录不同价格变动区间的次数计数器（u_p_1 到 u_p_4 和 d_p_1 到 d_p_4）。这些计数器用于跟踪市场在特定价格变动区间内的行为，这对于交易策略的决策过程至关重要。

    :param u_p_1: 记录涨幅在特定区间1的次数。
    :param d_p_1: 记录跌幅在特定区间1的次数。
    :param u_p_2: 记录涨幅在特定区间2的次数。
    :param d_p_2: 记录跌幅在特定区间2的次数。
    :param u_p_3: 记录涨幅在特定区间3的次数。
    :param d_p_3: 记录跌幅在特定区间3的次数。
    :param u_p_4: 记录涨幅在特定区间4的次数。
    :param d_p_4: 记录跌幅在特定区间4的次数。
    :param p: 当前的价格变动百分比，计算方式为 (current_price - last_date_price) / last_date_price。
    :param l_s1: 涨幅区间1的左限，表示涨幅区间1的起始点。
    :param l_s2: 涨幅区间2的左限，表示涨幅区间2的起始点。
    :param l_s3: 涨幅区间3的左限，表示涨幅区间3的起始点。
    :param l_s4: 涨幅区间4的左限，表示涨幅区间4的起始点。
    :param l_e1: 涨幅区间1的右限，表示涨幅区间1的结束点。
    :param l_e2: 涨幅区间2的右限，表示涨幅区间2的结束点。
    :param l_e3: 涨幅区间3的右限，表示涨幅区间3的结束点。
    :param l_e4: 涨幅区间4的右限，表示涨幅区间4的结束点。
    :param s_s1: 跌幅区间1的左限，表示跌幅区间1的起始点。
    :param s_s2: 跌幅区间2的左限，表示跌幅区间2的起始点。
    :param s_s3: 跌幅区间3的左限，表示跌幅区间3的起始点。
    :param s_s4: 跌幅区间4的左限，表示跌幅区间4的起始点。
    :param s_e1: 跌幅区间1的右限，表示跌幅区间1的结束点。
    :param s_e2: 跌幅区间2的右限，表示跌幅区间2的结束点。
    :param s_e3: 跌幅区间3的右限，表示跌幅区间3的结束点。
    :param s_e4: 跌幅区间4的右限，表示跌幅区间4的结束点。
    :return: 更新后的各个价格变动区间的计数器 u_p_1 到 u_p_4 和 d_p_1 到 d_p_4。
    """
    if l_s1 < p < l_e1:
        u_p_1 += 1  # 涨幅介于l_s1和l_e1之间次数加一
    if s_e1 < p < s_s1:
        d_p_1 += 1  # 跌幅介于s_s1和s_e1之间次数加一

    if l_s2 < p < l_e2:
        u_p_2 += 1  # 涨幅介于l_s2和l_e2之间次数加一
    if s_e2 < p < s_s2:
        d_p_2 += 1  # 跌幅介于s_s2和s_e2之间次数加一

    if l_s3 < p < l_e3:
        u_p_3 += 1  # 涨幅介于l_s3和l_e3之间次数加一
    if s_e3 < p < s_s3:
        d_p_3 += 1  # 跌幅介于于s_s3和s_e3之间次数加一

    if l_s4 < p < l_e4:
        u_p_4 += 1  # 涨幅介于l_s4和l_e4之间次数加一
    if s_e4 < p < s_s4:
        d_p_2 += 1  # 跌幅介于s_s4和s_e4之间次数加一

    return u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4


def update_short_place_uplimit_and_short_place_downlimit(short_place_downlimit, short_place_uplimit,
                                                         last_p, current_price, place_downlimit, place_uplimit):
    """
    此函数用于在开多仓成功后更新调整空仓的上下限。

    根据当前价格与上一次循环价格的比较结果，调整空仓的上下限，以反映市场的最新动态。这个调整是基于价格变动百分比（last_p_p），当价格变动百分比落在特定的区间内时，会相应地调整空仓的上下限，从而影响未来的开仓策略。

    :param short_place_uplimit: 当前空仓的上限，表示空仓可以触发的价格上限。
    :param short_place_downlimit: 当前空仓的下限，表示空仓可以触发的价格下限。
    :param last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    :param current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。
    :param place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的空仓下限。
    :param place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的空仓上限。
    :return: 调整后的空仓上下限（short_place_uplimit, short_place_downlimit）。
    """
    if last_p != 0:  # 确保last_p不为0,因为除数不能为0
        last_p_p = (current_price - last_p) / last_p
        if 0 < last_p_p < 0.0005:  # 涨幅变化不高，发生反转的可能性最大，调整空仓区间（下限左移，上限右移）
            short_place_downlimit = short_place_downlimit - 0.0005  # 左移0.0005
            short_place_uplimit = short_place_uplimit + 0.0005  # 右移0.0005
            if short_place_downlimit < 0.001:
                short_place_downlimit = 0.001
            if short_place_uplimit > 0.0065:
                short_place_uplimit = 0.0065
            return short_place_downlimit, short_place_uplimit

        elif 0.0005 < last_p_p < 0.001:  # 涨幅大于0.0005，小于0.001.。发生反转的可能性适中，微调整空仓区间（下限左移，上限右移）
            short_place_downlimit = short_place_downlimit - 0.0002  # 左移0.0002
            short_place_uplimit = short_place_uplimit + 0.0002  # 右移0.0002
            if short_place_downlimit < 0.001:
                short_place_downlimit = 0.001
            if short_place_uplimit > 0.0065:
                short_place_uplimit = 0.0065
            return short_place_downlimit, short_place_uplimit

        elif last_p_p > 0.001:  # 在涨幅超过0.001的情况下，说明反转可能小，调整空仓区间（下限右移，上限左移）
            short_place_downlimit = short_place_downlimit + 0.0002  # 右移0.0002
            short_place_uplimit = short_place_uplimit - 0.0002  # 左移0.0002
            if short_place_downlimit > place_downlimit:  # 回到原始下限
                short_place_downlimit = place_downlimit
            if short_place_uplimit < place_uplimit:  # 回到原始上限
                short_place_uplimit = place_uplimit
            return short_place_downlimit, short_place_uplimit

    return short_place_downlimit, short_place_uplimit


def update_long_place_uplimit_and_long_place_downlimit(long_place_uplimit, long_place_downlimit,
                                                       last_p, current_price, place_downlimit, place_uplimit
                                                       ):
    """
    此函数用于在开空仓成功后更新调整多仓的上下限。

    根据当前价格与上一次循环价格的比较结果，调整多仓的上下限，以反映市场的最新动态。这个调整是基于价格变动百分比（last_p_p），当价格变动百分比落在特定的区间内时，会相应地调整多仓的上下限，从而影响未来的开仓策略。

    :param long_place_uplimit: 当前多仓的上限，表示多仓可以触发的价格上限。
    :param long_place_downlimit: 当前多仓的下限，表示多仓可以触发的价格下限。
    :param last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    :param current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。
    :param place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的多仓下限。
    :param place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的多仓上限。
    :return: 调整后的多仓上下限（long_place_uplimit, long_place_downlimit）。
    """
    if last_p != 0:  # 避免0除
        last_p_p = (current_price - last_p) / last_p
        if 0 > last_p_p > -0.0005:  # 跌幅幅变化不高，发生反转的可能性最大，调多仓的区间（下限左移，上限右移）
            long_place_downlimit = long_place_downlimit - 0.0005  # 左移0.0005
            long_place_uplimit = long_place_uplimit + 0.0005  # 右移0.0005
            if long_place_downlimit < 0.001:
                long_place_downlimit = 0.001
            if long_place_uplimit > 0.0065:
                long_place_uplimit = 0.0065
            return long_place_downlimit, long_place_uplimit

        elif -0.0005 > last_p_p > -0.001:  # 跌幅幅大于0.005，小于0.001.。发生反转的可能性适中，微调多仓区间（下限左移，上限右移）
            long_place_downlimit = long_place_downlimit - 0.0002  # 左移0.0002
            long_place_uplimit = long_place_uplimit + 0.0002  # 右移0.0002
            if long_place_downlimit < 0.001:
                long_place_downlimit = 0.001
            if long_place_uplimit > 0.0065:
                long_place_uplimit = 0.0065
            return long_place_downlimit, long_place_uplimit

        elif last_p_p > -0.001:  # 在跌幅超过0.001的情况下，说明反转可能小，调整仓区间(下限右移，上限左移)
            long_place_downlimit = long_place_downlimit + 0.0002  # 右移0.0002
            long_place_uplimit = long_place_uplimit - 0.0002  # 左移0.0002
            if long_place_downlimit > place_downlimit:  # 回到原始下限
                long_place_downlimit = place_downlimit
            if long_place_uplimit < place_uplimit:  # 回到原始上限
                long_place_uplimit = place_uplimit
            return long_place_downlimit, long_place_uplimit

    return long_place_downlimit, long_place_uplimit


def update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(long_place_downlimit, long_place_uplimit,
                                                                   place_downlimit,
                                                                   place_uplimit, l_c):
    """
    此函数用于在开多仓次数达到一定阈值时调整多仓的上下限。

    当开多仓的次数计数器（l_c）超过某个特定值时，意味着可能存在频繁的开多仓操作。为了降低交易频率和风险，此函数会调整多仓的上下限，使得未来的开多仓操作更加谨慎。

    :param long_place_downlimit: 当前多仓的下限，表示多仓可以触发的价格下限。
    :param long_place_uplimit: 当前多仓的上限，表示多仓可以触发的价格上限。
    :param place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的多仓下限。
    :param place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的多仓上限。
    :param l_c: 开多仓的次数计数器，用于确定是否需要调整多仓的上下限。
    :return: 调整后的多仓上下限（long_place_downlimit, long_place_uplimit）。
    """
    if long_place_downlimit < place_downlimit + 0.0015:
        long_place_downlimit = long_place_downlimit + 0.0001 * l_c
        if long_place_downlimit > 0.0025:  # 调整后不能大于0.0025
            long_place_downlimit = 0.0025

    if long_place_uplimit < place_uplimit + 0.0035:
        long_place_uplimit = long_place_uplimit + 0.0001 * l_c
        if long_place_uplimit > 0.0065:  # 调整后不能大于0.0055
            long_place_uplimit = 0.0065

    return long_place_downlimit, long_place_uplimit


def update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(short_place_downlimit, short_place_uplimit,
                                                                     place_downlimit,
                                                                     place_uplimit, s_c):
    """
    此函数用于在开空仓次数达到一定阈值时调整空仓的上下限。

    当开空仓的次数计数器（s_c）超过某个特定值时，意味着可能存在频繁的开空仓操作。为了降低交易频率和风险，此函数会调整空仓的上下限，使得未来的开空仓操作更加谨慎。

    :param short_place_downlimit: 当前空仓的下限，表示空仓可以触发的价格下限。
    :param short_place_uplimit: 当前空仓的上限，表示空仓可以触发的价格上限。
    :param place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的空仓下限。
    :param place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的空仓上限。
    :param s_c: 开空仓的次数计数器，用于确定是否需要调整空仓的上下限。
    :return: 调整后的空仓上下限（short_place_downlimit, short_place_uplimit）。
    """

    if short_place_downlimit < place_downlimit + 0.0015:  # 不能超过 place_downlimit + 0.0025
        short_place_downlimit = short_place_downlimit + 0.0001 * s_c
        if short_place_downlimit > 0.0025:  # 调整后不能大于0.0025
            short_place_downlimit = 0.0025

    if short_place_uplimit < place_uplimit + 0.0035:  # 不能超过 lace_uplimit + 0.0035
        short_place_uplimit = short_place_uplimit + 0.0001 * s_c
        if short_place_uplimit > 0.0065:  # 调整后不能大于0.0055
            short_place_uplimit = 0.0065

    return short_place_downlimit, short_place_uplimit


def save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit, short_place_uplimit,
                   l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4, n_sz):
    """
    此函数用于在策略管理线程发生错误或退出时保存当前的动态参数到文件。

    这些参数包括开仓上下限、涨跌幅区间计数器、随机时间区间等，它们会被保存到一个JSON文件中，以便在下一次程序启动时能够加载这些参数，从而保持策略的连续性和状态的持久性。

    :param long_place_downlimit: 多头开仓的下限价格变动百分比。
    :param long_place_uplimit: 多头开仓的上限价格变动百分比。
    :param short_place_downlimit: 空头开仓的下限价格变动百分比。
    :param short_place_uplimit: 空头开仓的上限价格变动百分比。
    :param l_c: 多头开仓次数计数器。
    :param s_c: 空头开仓次数计数器。
    :param u_p_1: 涨幅区间1的计数器。
    :param u_p_2: 涨幅区间2的计数器。
    :param u_p_3: 涨幅区间3的计数器。
    :param u_p_4: 涨幅区间4的计数器。
    :param d_p_1: 跌幅区间1的计数器。
    :param d_p_2: 跌幅区间2的计数器。
    :param d_p_3: 跌幅区间3的计数器。
    :param d_p_4: 跌幅区间4的计数器。
    :param n_sz: 实际的minSz整数倍
    :return: 无返回值，函数执行后会将参数保存到文件中。
    """
    data = {'long_place_downlimit': long_place_downlimit,
            'long_place_uplimit': long_place_uplimit,
            'short_place_downlimit': short_place_downlimit,
            'short_place_uplimit': short_place_uplimit,
            'l_c': l_c,
            's_c': s_c,
            'u_p_1': u_p_1,
            'u_p_2': u_p_2,
            'u_p_3': u_p_3,
            'u_p_4': u_p_4,
            'd_p_1': d_p_1,
            'd_p_2': d_p_2,
            'd_p_3': d_p_3,
            'd_p_4': d_p_4,
            'n_sz': n_sz
            }
    with open('parameter.txt', 'w') as f:
        # 通过将 buffering 参数设置为 0，可以让文件以无缓冲的方式进行写入操作，
        # 这样写入的数据会立即被写入到磁盘文件中，而不会在内存中进行缓冲。
        f.write(json.dumps(data))  # json.dumps() 将python对象转换为json字符串并保存到文件


def load_parameter():
    """
    这个方法会在程序第一次启动的时候从parameter.txt中加载一些程序需要的动态参数
    """
    with open('parameter.txt', 'r') as f:
        data = json.loads(f.read())  # json.loads() 将json字符串转换为python对象
        return (data['long_place_downlimit'], data['long_place_uplimit'],
                data['short_place_downlimit'], data['short_place_uplimit'],
                data['l_c'], data['s_c'], data['u_p_1'], data['u_p_2'],
                data['u_p_3'], data['u_p_4'], data['d_p_1'], data['d_p_2'],
                data['d_p_3'], data['d_p_4'],data['n_sz'])


def take_progit(o: MyOkx, instId: str, leverage: int, place_uplimit: float, place_downlimit: float):
    """
    此函数用于执行止盈操作，并在操作后重新初始化相关参数。

    当触发止盈条件时，此函数会被调用来平掉当前持有的仓位，并根据市场的最新状态重新设置交易参数，以准备下一次的交易决策。

    :param o: MyOkx类的实例，用于与OKX交易所API进行交互。
    :param instId: 交易对的标识符，例如'ETH-USDT-SWAP'。
    :param leverage: 交易使用的杠杆倍数。
    :param place_uplimit: 开仓的涨幅上限。
    :param place_downlimit: 开仓的跌幅下限。
    :return: 如果止盈操作成功，返回更新后的参数集合，包括涨跌幅区间计数器和随机时间区间等；如果失败，则返回None。
    """
    global lq
    close_positions_re = o.close_positions(instId=instId, leverage=leverage, ordType='market',
                                           tdMode='cross', limit_uplRatio=0)
    if close_positions_re:
        if close_positions_re == 1:
            lq.push(('止盈记录', 'Success', '一键止盈成功'))

            # 初始化一些参数：包括：
            # 各个u_p和d_p用于记录涨跌幅分别在某一个区间的次数。初始为0
            # random_start和random_end用于记录随机时间区间。random_start和random_end初始为10和20
            # long_place_uplimit和long_place_downlimit。开多仓的区间上下限
            # short_place_uplimit和short_place_downlimit。开空仓的区间上下限
            # l_c和s_c用于记录交易多头还是空头的次数。初始为0
            (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
             random_end,
             long_place_uplimit, long_place_downlimit, short_place_uplimit,
             short_place_downlimit,
             l_c, s_c) = (
                init_arguments(
                    place_uplimit=place_uplimit,
                    place_downlimit=place_downlimit))
            return (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                    random_end,
                    long_place_uplimit, long_place_downlimit, short_place_uplimit,
                    short_place_downlimit,
                    l_c, s_c)
        else:
            lq.push(('止盈记录', 'Error', '一键止盈失败'))
            return None


def switch_thread(host: str, username: str, password: str, database: str, port: int = 3306, table: str = 'switch'):
    """
    这个管理函数会定时从mysql中的database数据库中的'switch'表中获取最后一行的值作为控制程序的退出，当获取的值为1时，它会更改should_exit为False(表示程序保持运行),
    当当获取的值为0时，更改为False(表示程序停止运行)
    :param host:
    :param username:
    :param password:
    :param database:
    :param port:
    :param table:
    :return:
    """
    global should_exit
    global s_finished_event
    global lq
    time.sleep(30)
    while True:
        try:
            if s_finished_event.is_set() or should_exit:
                break
            with pymysql.connect(host=host, user=username, password=password, database=database, port=port) as client:
                df = pd.read_sql(f"SELECT id,程序开关 FROM {table} ORDER BY id DESC LIMIT 1", con=client)
                re = int(df['程序开关'].iloc[0])
                if re == 1:
                    should_exit = False
                if re == 0:
                    should_exit = True
                    lq.push(('程序状态', 'Info', '程序将停止运行'))

            time.sleep(30)
        except:
            should_exit = True
            s_finished_event.set()
            break


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
    global s_finished_event
    global log_table_name  # 日志表
    global should_exit
    global lq  # 日志队列

    time.sleep(30)
    while True:
        try:
            if s_finished_event.is_set() or should_exit:  # 事件对象被设置，说明s进程结束
                # 确保r_d的数据被完全写入数据库
                log_to_mysql(mysql_host=mysql_host, mysql_username=mysql_username, mysql_password=mysql_password,
                             mysql_database=mysql_database, mysql_log_table=log_table_name, max_logs=fq, log_queue=lq,
                             mysql_port=mysql_port)
                break

            i = 0  # 重试计数器
            while True:
                if log_to_mysql(mysql_host=mysql_host, mysql_username=mysql_username, mysql_password=mysql_password,
                                mysql_database=mysql_database, mysql_log_table=log_table_name, max_logs=fq, log_queue=lq,
                                mysql_port=mysql_port) is False:  # 该函数可以一次可以批量处理fq条日志到数据库中
                    if i < 3:  # 最多重试3次
                        print("批量处理日志信息到mysql数据库失败，10秒后重试")
                        i += 1
                        time.sleep(10)
                    else:
                        send_email(sender, receiver, sender_password, subject='来自okx自动化策略程序的运行错误的提醒:',
                                   content='线程：logs_manager_thread\n日志批处理失败\n请检查网络')
                        break  # 这里后面可以添加发邮件提醒用户功能。
                else:
                    break  # 如果批量处理日志成功，就跳出循环。

            time.sleep(5 * 60)  # 五分钟执行一次
        except:
            should_exit = True
            s_finished_event.set()
            break


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
    global s_finished_event
    global r_d
    global data_table_name
    global should_exit
    time.sleep(30)
    while True:
        try:
            if s_finished_event.is_set() or should_exit:  # 事件对象被设置，说明s进程结束
                # 确保r_d的数据被完全写入数据库
                real_time_data(r_d, host, port, username, password, database, data_table_name)
                break

            if real_time_data(r_d, host, port, username, password, database, data_table_name):
                time.sleep(5 * 60)
            else:
                send_email(sender, receiver, sender_password, subject='来自okx自动化策略程序的运行错误的提醒:',
                           content='线程：real_time_data_manager_thread\n实时数据批处理失败\n请检查网络')
                break
        except:
            should_exit = True
            s_finished_event.set()
            break


if __name__ == '__main__':
    # 连接MySQL数据库
    mydb = pymysql.connect(
        host="101.34.59.205",
        user="云服务器mysql", # 此账户只有读权限
        password="yshhsq31",
        database="自动化交易程序配置参数"
    )

    mycursor = mydb.cursor()

    # 从strategy_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM strategy_manager_thread_arguments")
    result_strategy = mycursor.fetchone()
    strategy_thread = None
    if result_strategy:
        strategy_args = {
            'mysql_host': result_strategy[1],
            'mysql_username': result_strategy[2],
            'mysql_password': result_strategy[3],
            'mysql_coin_database': result_strategy[4],
            'mysql_coin_day_date_table': result_strategy[5],
            'okx_api_key': result_strategy[6],
            'okx_secret_key': result_strategy[7],
            'okx_passphrase': result_strategy[8],
            'instId': result_strategy[9],
            'leverage': int(result_strategy[10]),
            'sender': result_strategy[11],
            'receiver': result_strategy[12],
            'sender_password': result_strategy[13],
            'place_position_nums': result_strategy[14],
            'place_uplimit': (result_strategy[15]),
            'place_downlimit': (result_strategy[16]),
            'mysql_port': (result_strategy[17]),
            'sz': result_strategy[18],
            'l_s1': result_strategy[19],
            'l_s2': result_strategy[20],
            'l_s3': result_strategy[21],
            'l_s4': result_strategy[22],
            'l_e1': result_strategy[23],
            'l_e2': result_strategy[24],
            'l_e3': result_strategy[25],
            'l_e4': result_strategy[26],
            's_s1': result_strategy[27],
            's_s2': result_strategy[28],
            's_s3': result_strategy[29],
            's_s4': result_strategy[30],
            's_e1': result_strategy[31],
            's_e2': result_strategy[32],
            's_e3': result_strategy[33],
            's_e4': result_strategy[34],
            'l_c_limit': result_strategy[35],
            's_c_limit': result_strategy[36],
            'limit_uplRatio': result_strategy[37],
        }
        strategy_thread = Thread(target=strategy_manager_thread, kwargs=strategy_args)

    # 从logs_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM logs_manager_thread_arguments")
    result_logs = mycursor.fetchone()
    logs_thread = None
    if result_logs:
        logs_args = {
            'mysql_host': result_logs[1],
            'mysql_port': result_logs[2],
            'mysql_username': result_logs[3],
            'mysql_password': result_logs[4],
            'mysql_database': result_strategy[4],
            'sender': result_logs[5],
            'receiver': result_logs[6],
            'sender_password': result_logs[7],
            'fq': result_logs[8]
        }
        logs_thread = Thread(target=logs_manager_thread, kwargs=logs_args)

    # 从real_time_data_manager_thread_arguments表中获取参数并启动线程
    mycursor.execute("SELECT * FROM real_time_data_manager_thread_arguments")
    result_real_time = mycursor.fetchone()
    real_time_thread = None
    if result_real_time:
        real_time_args = {
            'host': result_real_time[1],
            'port': result_real_time[2],
            'username': result_real_time[3],
            'password': result_real_time[4],
            'database': result_strategy[4],
            'sender': result_real_time[5],
            'receiver': result_real_time[6],
            'sender_password': result_real_time[7]
        }
        real_time_thread = Thread(target=real_time_data_manager_thread, kwargs=real_time_args)

    switch_thread = Thread(target=switch_thread,
                           args=(result_logs[1], result_logs[3], result_logs[4], result_strategy[4], result_real_time[2]))

    mycursor.close()
    mydb.close()

    # 启动线程
    if strategy_thread:
        strategy_thread.start()

    if logs_thread:
        logs_thread.start()

    if real_time_thread:
        real_time_thread.start()

    if switch_thread:
        switch_thread.start()

    # 阻塞主线程
    if strategy_thread:
        strategy_thread.join()

    if logs_thread:
        logs_thread.join()

    if real_time_thread:
        real_time_thread.join()

    if switch_thread:
        switch_thread.join()