"""
这个模块是交易核心，包括交易管理、日志管理、实时数据管理。它负责执行交易策略并管理相关操作。
"""

" 内置模块："
import datetime
import logging
import random
import sys
import time
from datetime import datetime as dt
from datetime import timedelta

" 自定义模块："
from mysqldata import sava_all_data_to_mysql, create_control_program_switch_table
from myokx import MyOkx, get_ticker_last_price
from logs import create_log_table
from mymail import send_email
from strategy import go_long_signal, go_short_signal, predict
from getdata import get_btc_sol_eth_doge_last_price_mean_normalized
import function
import global_vars

# 设置基本的日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
                            limit_uplRatio: float = -0.5,
                            lower_take_profit:float = 0.012
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
    :param lower_take_profit: 止盈下限,即止盈下限为当前价格与前一天价格变化百分比的最小值
    :return: 无返回值，此线程函数负责执行交易策略并管理相关操作。
    """
    global_vars.lq.push(('交易线程-状态信息', 'info', '交易线程启动'))  # 启动交易线程
    ppn = place_position_nums  # 计划持仓时，实际拥有的最大头寸数量
    before_mean_p: float = 0  # 上一次btc,sol,eth,doge的当前最新价格较昨收盘价的变化百分比变化均值
    before_five_current_data_average = 0  # 上一次五个当前交易对的实时价格的平均值
    current_five_current_data_average = 0  # 当前五个当前交易对的实时价格的平均值

    # 前五个当前交易对的实时价格数据
    top_five_current_data = []

    # 记录交易类型，0表示无交易，1表示开多，-1表示开空，2表示止盈平多，-2表示止盈平空，3表示止损
    trade_type: int = 0

    before_bidSz: float = 0  # 上一次买入量
    before_askSz: float = 0  # 上一次卖出量
    before_vol24h: float = 0  # 上一次24小时成交量

    last_p_p: float = 0  # 当前价格与上一次价格变化百分比

    # 设置随机时间区间，随机休眠的时间会从这个区间内生成。
    random_start = 10  # 随机时间的左区间
    random_end = 20  # 随机时间的右区间

    before_price: float = 0  # 上一次循环的价格

    # 实例化MyOkx实例
    o = MyOkx(okx_api_key, okx_secret_key, okx_passphrase)

    # 从配置文件中加载下列参数:
    (long_place_downlimit, long_place_uplimit, short_place_downlimit, short_place_uplimit,
     l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4, n_sz, loss, profit) = function.load_parameter()

    # 创建控制程序开关的表
    while True:
        try:
            create_control_program_switch_table(host=mysql_host, username=mysql_username, password=mysql_password,
                                                database=mysql_coin_database, table='switch')
            global_vars.lq.push(('交易线程-创建控制程序开关表', 'Success', '创建控制程序开关表成功'))
            print('创建控制程序开关表成功')
            break
        except Exception as e:
            print(f'创建控制程序开关表失败:{e}，正在重试...')
            global_vars.lq.push(('交易线程-创建控制程序开关表', 'Error', f'创建控制程序开关表失败:{e}，正在重试...'))
            time.sleep(3)

    today = datetime.datetime.now().strftime('%Y-%m-%d')  # today是当前时间
    today_obj = dt.strptime(today, "%Y-%m-%d")  # 将字符串转换为时间对象
    yesterday_obj = today_obj - timedelta(days=1)  # 昨天的时间对象
    yesterday = yesterday_obj.strftime("%Y-%m-%d")  # 昨天的时间字符串
    global_vars.data_table_name = today.replace('-', '_') + '实时数据'

    c = 0  # 重试计数器
    while True:

        # 生成本次循环结束后的休眠时间
        random_time = random.randint(random_start, random_end)

        if global_vars.s_finished_event:
            global_vars.lq.push(('交易线程-状态信息', 'info', '交易线程停止'))
            break
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            " 新的一天更新逻辑 "
            if today != yesterday:

                global_vars.data_table_name = today.replace('-', '_') + '实时数据'  # 创建用于存储新的一天的实时数据的新表名

                today_str = today.replace('-', '_')
                log_table = f'{today_str}_{leverage}X_logs'  # 创建用于存储新的一天的日志数据的新表名
                global_vars.log_table_name = log_table

                # 在数据库中创建日志表
                if create_log_table(mysql_host=mysql_host, mysql_port=mysql_port, mysql_username=mysql_username,
                                    mysql_password=mysql_password,
                                    mysql_database=mysql_coin_database, mysql_log_table=log_table):
                    global_vars.lq.push(('交易线程-创建日志表', 'Success', '创建新日期的日志表'))
                else:
                    # 尝试发送邮件通知后，保存参数到配置文件，再停止程序

                    global_vars.s_finished_event = True  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止

                    send_email(sender=sender, receiver=receiver, password=sender_password,
                               subject='来自okx自动化策略程序的运行错误的提醒:',
                               content="线程：strategy_manager_thread"
                                       "\n创建新的日志表失败,退出程序"
                                       "\n请你前往服务器检查服务器网络,"
                               )
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

                        global_vars.lq.push(('交易线程-保存前一天的收盘价', 'Success', f'保存前一天收盘价到数据库成功'))
                        break
                    except Exception as e:
                        if a < 3:
                            global_vars.lq.push(
                                ('交易线程-保存前一天的收盘价', 'Error', f'保存前一天收盘价到数据库失败:{e},5秒后重试'))
                            a += 1
                            time.sleep(5)
                        else:
                            # 多次保存前一天的数据失败
                            global_vars.s_finished_event = True  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止

                            send_email(sender=sender, receiver=receiver, password=sender_password,
                                       subject='来自okx自动化策略程序的运行错误的提醒:',
                                       content="发生在:strategy_manager_thread线程。\n"
                                               "错误位置：将前一天的日数据保存到数据库中时失败。\n"
                                               f"错误原因：{e}\n")
                            break

                if global_vars.s_finished_event: continue  # 保存前一天的日数据到数据库中去失败，应该退出程序,否则继续执行

                yesterday = today  # 更新前一天

                # 新的一天，初始化一些参数：
                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start, random_end,
                 long_place_uplimit,
                 long_place_downlimit, short_place_uplimit, short_place_downlimit, l_c, s_c) = function.init_arguments(
                    place_uplimit=place_uplimit,
                    place_downlimit=place_downlimit)

            " 交易前准备 "
            current_coin_data, current_price, p = get_ticker_last_price(
                instId)  # 获取当前交易类型的最新信息,的所有信息，交易对的最新价格信息，当前最新价格较昨收盘价的变化百分比变化
            current_bidSz, current_askSz = float(current_coin_data["bidSz"]), float(
                current_coin_data["askSz"])  # 从交易类型的最新信息中获取当前交易类类型的最新买卖深度
            current_vol24h = float(current_coin_data['vol24h'])  # 从交易类型的最新信息中获取当前交易类型的24小时交易量
            current_mean_p = get_btc_sol_eth_doge_last_price_mean_normalized()  # 获取BTC,SOL,ETH,DOGE的最新价格标准化的平均值
            now = datetime.datetime.now()  # 获取此时的时间
            formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")  # 格式化日期和时间
            current_position_nums = 0  # 当前instId类型的仓位头寸，初始化为0

            current_positions = o.get_positions()  # 获取所有仓位信息
            if current_positions:  # 如果有当前交易类型的仓位，那么获取当前交易类型的头寸信息，注意，可能存在多头和空头的仓位，所以头寸信息空头取负值，多头取正值
                for position in current_positions:
                    if position["instId"] == instId:  # 只获取当前交易类型的仓位信息
                        pos = float(position["pos"])
                        if pos < 0:  # 说明当前交易类型有空头仓位
                            current_position_nums = float(position["notionalUsd"])  # 获取空头仓位头寸信息，取负值
                            current_position_nums = -current_position_nums
                            break
                        elif pos > 0:  # 说明当前交易类型有多头仓位
                            current_position_nums = float(position["notionalUsd"])  # 获取多头仓位头寸信息，取正值
                            break

            # 计算当前最新价格较上一周期价格的变化百分比变化
            if before_price != 0:  # 程序初次运行last_p被初始化为0，避免初次运行出现零除
                last_p_p = (current_price - before_price) / before_price

            # 根据p值所落在哪一个区间上来更新这些区间计数器：u_p_1到u_p_4，d_p_1到d_p_4
            u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4 = function.update_u_p_and_d_p(u_p_1, d_p_1, u_p_2,
                                                                                                 d_p_2,
                                                                                                 u_p_3, d_p_3, u_p_4,
                                                                                                 d_p_4,
                                                                                                 p, l_s1, l_s2,
                                                                                                 l_s3, l_s4, l_e1, l_e2,
                                                                                                 l_e3,
                                                                                                 l_e4, s_s1, s_s2, s_s3,
                                                                                                 s_s4
                                                                                                 , s_e1, s_e2, s_e3,
                                                                                                 s_e4)

            # 计算前五个周期当前交易类型的价格平均值
            if len(top_five_current_data) < 5:  # top_five_current_data是一个列表，放有前五个周期当前交易类型的最新价格数据
                top_five_current_data.append(current_price)  # 将最新的一个周期最新价格数据添加到列表中
            if len(top_five_current_data) == 5:  # 当top_five_current_data列表中已有五个元素时，计算前五个周期当前交易类型的最新价格平均值
                current_five_current_data_average = sum(top_five_current_data) / 5
                top_five_current_data.pop(0)  # pop(0)表示删除列表中第一个元素，即删除最旧的一个周期数据

            " 开仓逻辑 "
            # 开多仓逻辑
            if go_long_signal(long_place_downlimit, long_place_uplimit, p, last_p_p, before_five_current_data_average,
                              current_five_current_data_average, before_mean_p, current_mean_p,
                              l_c, l_c_limit, before_bidSz, current_bidSz, before_vol24h, current_vol24h) and predict(
                current_price,
                before_price,
                before_five_current_data_average,
                current_five_current_data_average,
                before_mean_p,
                current_mean_p,
                before_bidSz, current_bidSz,
                before_askSz,
                current_askSz,
                before_vol24h, current_vol24h):

                if (current_position_nums <= 0) or (
                        current_position_nums > 0 and abs(current_position_nums) < ppn - 10):
                    """ 
                    三种开多仓的情况：
                        1. 当前有多仓，但仓位小于ppn-10 USDT，则可以继续开多仓
                        2. 当前有空仓，则可以开多仓
                        3. 当前无仓，则可以开多仓
                    """
                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='buy', ordType='market',
                                                    lever=leverage,
                                                    sz=n_sz)  # d包含了交易操作后返回的结果信息，Sz是下单的实际数量：Sz = n_sz * minSz，n_sz是minSz的整数倍
                    if d['code'] != '0':
                        global_vars.lq.push(('交易线程-交易记录', 'Error', f'买入失败:{d}'))
                    else:
                        global_vars.lq.push(('交易线程-交易记录', 'Success', f'买入成功'))

                        l_c += 1  # 开多仓计数器加一

                        # 开多仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if l_c >= 3:
                            long_place_downlimit, long_place_uplimit = (
                                function.update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(
                                    long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, l_c=l_c))

                        #  如果交易成功，减小下一次如果发生空仓交易的触发下限和上限。因为如果下一次反转时，开反仓区间靠近，可以减小损失。
                        short_place_downlimit, short_place_uplimit = (
                            function.update_short_place_uplimit_and_short_place_downlimit(
                                short_place_downlimit=short_place_downlimit, short_place_uplimit=short_place_uplimit,
                                before_price=before_price, current_price=current_price,
                                place_downlimit=place_downlimit, place_uplimit=place_uplimit))
                        trade_type = 1

            # 这是开空仓的逻辑
            elif go_short_signal(short_place_downlimit, short_place_uplimit, p, last_p_p,
                                 before_five_current_data_average,
                                 current_five_current_data_average, before_mean_p, current_mean_p,
                                 s_c, s_c_limit, before_askSz, current_askSz, before_vol24h,
                                 current_vol24h) and predict(current_price,
                                                             before_price,
                                                             before_five_current_data_average,
                                                             current_five_current_data_average,
                                                             before_mean_p,
                                                             current_mean_p,
                                                             before_bidSz, current_bidSz,
                                                             before_askSz,
                                                             current_askSz,
                                                             before_vol24h, current_vol24h):

                if (current_position_nums >= 0) or (
                        current_position_nums < 0 and abs(current_position_nums) < ppn - 10):
                    """
                    三种开空仓的情况：
                        1.当前持有多仓，直接开空仓
                        2. 当前有持空仓，但持仓小于ppn-10 USDT，直接开空仓
                        3. 当前没有持仓，直接开空仓   
                    """
                    d, Sz = o.place_agreement_order(instId=instId, tdMode='cross', side='sell', ordType='market',
                                                    lever=leverage, sz=n_sz)
                    if d['code'] != '0':
                        global_vars.lq.push(('交易线程-交易记录', 'Error', f'买入失败:{d}'))
                    else:
                        global_vars.lq.push(('交易线程-交易记录', 'Success', f'卖出成功'))

                        s_c += 1  # 开多仓计数器加一

                        # 开空仓计数器大于3次，说明当前交易太频繁,调整开空区间，上下限调整幅度加大，而且是为了减小交易频率
                        if s_c >= 3:
                            short_place_downlimit, short_place_uplimit = (
                                function.update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(
                                    short_place_downlimit=short_place_downlimit,
                                    short_place_uplimit=short_place_uplimit,
                                    place_downlimit=place_downlimit, place_uplimit=place_uplimit, s_c=s_c))

                        #  如果交易成功，根据当前价格和上一次价格，调整下一次反转时开仓区间。
                        long_place_downlimit, long_place_uplimit = function.update_long_place_uplimit_and_long_place_downlimit(
                            long_place_downlimit=long_place_downlimit, long_place_uplimit=long_place_uplimit,
                            before_price=before_price, current_price=current_price,
                            place_downlimit=place_downlimit, place_uplimit=place_uplimit)
                        trade_type = -1

            " 获利逻辑 "
            if p > float(lower_take_profit) or p < -float(lower_take_profit):

                for position in current_positions:  # 遍历持仓列表获取当前仓位信息
                    if position["instId"] == instId:
                        today_pos = float(position["pos"])  # 获取持仓方向，1为多仓，-1为空仓

                        # 如果涨幅超过25% 或者 跌幅超过25% ，那么就止盈
                        if p > 0.25 or p < -0.25:
                            while True:

                                if today_pos > 0:  # 多仓获利，对应p超过25%的情况
                                    trade_type = 2  # 设置交易类型为2，表示止盈
                                    re = function.take_progit(o=o, instId=instId, leverage=leverage,
                                                              place_uplimit=place_uplimit,
                                                              place_downlimit=place_downlimit)  # 执行止盈操作

                                    # 如果止盈操作成功，take_progit会返回需要初始化的参数元组，如果止盈操作失败会返回None
                                    if re:
                                        (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                         random_end,
                                         long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                         short_place_downlimit,
                                         l_c, s_c) = re  # 解包返回的元组，获取需要初始化的参数

                                        ppn = place_position_nums  # ppn更新为用户配置的参数
                                        n_sz = sz  # n_sz更新为用户配置的参数
                                        loss = 0  # 获利累计清零

                                        global_vars.lq.push(('交易线程-止盈记录', 'Success', '止盈【多,超0.25方向】成功'))
                                        break
                                    else:
                                        global_vars.lq.push(('交易线程-止盈记录', 'Error', '止盈【多,超0.25方向】失败'))

                                elif today_pos < 0:  # 空仓获利，对应p超过-25%的情况
                                    trade_type = -2
                                    re = function.take_progit(o=o, instId=instId, leverage=leverage,
                                                              place_uplimit=place_uplimit,
                                                              place_downlimit=place_downlimit)
                                    if re:
                                        (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                         random_end,
                                         long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                         short_place_downlimit,
                                         l_c, s_c) = re

                                        ppn = place_position_nums
                                        n_sz = sz
                                        loss = 0

                                        global_vars.lq.push(('交易线程-止盈记录', 'Success', '止盈【空,超0.25方向】成功'))
                                        break
                                    else:
                                        global_vars.lq.push(('交易线程-止盈记录', 'Error', '止盈【空,超0.25方向】失败'))

                        # 由区间的计数器触发止盈的操作
                        elif today_pos > 0 and ((u_p_1 > 50) or (u_p_2 >25) or (u_p_3 > 13) or (u_p_4 > 6)):
                            trade_type = 2
                            re = function.take_progit(o=o, instId=instId, leverage=leverage,
                                                      place_uplimit=place_uplimit,
                                                      place_downlimit=place_downlimit)
                            if re:
                                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                 random_end,
                                 long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                 short_place_downlimit,
                                 l_c, s_c) = re

                                ppn = place_position_nums
                                n_sz = sz
                                loss = 0

                                global_vars.lq.push(('交易线程-止盈记录', 'Success', '止盈【多,区间计数器触发】成功'))
                            else:
                                global_vars.lq.push(('交易线程-止盈记录', 'Error', '止盈【多,区间计数器触发】失败'))

                        # 如果d_p_1,到d_p_4其中一个大于设定值，且持有空仓，那么就平空仓。
                        elif today_pos < 0 and ((d_p_1 > 50) or (d_p_2 > 25) or (d_p_3 > 13) or (d_p_4 >6)):
                            trade_type = -2
                            re = function.take_progit(o=o, instId=instId, leverage=leverage,
                                                      place_uplimit=place_uplimit,
                                                      place_downlimit=place_downlimit)
                            if re:
                                (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4, random_start,
                                 random_end,
                                 long_place_uplimit, long_place_downlimit, short_place_uplimit,
                                 short_place_downlimit,
                                 l_c, s_c) = re

                                ppn = place_position_nums
                                n_sz = sz
                                loss = 0

                                global_vars.lq.push(('交易线程-止盈记录', 'Success', '止盈【空,区间计数器触发】成功'))

                            else:
                                global_vars.lq.push(('交易线程-止盈记录', 'Error', '止盈【空,区间计数器触发】失败'))
                        else:
                            global_vars.lq.push(
                                ('交易线程-状态更新', 'Info', '当前价格符合获利价格区间但是没有触发条件'))
                            break  # 跳出获利逻辑的for循环

                    global_vars.lq.push(('交易线程-状态更新', 'Info', f'当前没有持有{instId}类型的仓位'))

            " 止损逻辑 "
            # 进入close_positions方法,这个方法会获取亏损比然后根据用户配置的limit_uplRatio决定是否执行止损操作
            close_positions_re = o.close_positions(instId=instId, leverage=leverage, ordType='market', tdMode='cross',
                                                   limit_uplRatio=limit_uplRatio)
            if close_positions_re:  # close_positions没有返回None值，说明没有出现什么错误。
                if close_positions_re == 1:  # 发生了止损操作
                    trade_type = 3  # 交易类型标记为3，表示止损操作

                    # 获取刚刚平仓的历史仓位信息
                    while True:
                        last_loss = float(o.get_positions_history()['realizedPnl'])  # 获取亏损金额
                        if last_loss > 0:  # 如果金额大于0，就继续等待
                            global_vars.lq.push(('交易线程-止损记录', 'Info', '等待平仓历史仓位信息更新'))
                            time.sleep(10)
                        else:
                            global_vars.lq.push(
                                ('交易线程-止损记录', 'Success', '平仓历史仓位信息更新成功,成功获取亏损金额'))
                            # 获取亏损金额
                            loss = float(loss) + abs(last_loss)
                            # 计算下一次大概的盈利金额
                            profit = loss * 1.3
                            # 下一次计划持仓量
                            x = (profit / 0.6) * leverage  # 假设0.5是下一次盈利的收益率
                            # 更新n_sz
                            n_sz = (x / current_price) * leverage
                            # 取整
                            n_sz = round(n_sz)
                            ppn = n_sz * current_price / leverage - 50
                            break

                        global_vars.lq.push(('交易线程-止损记录', 'Info', f'更新n_sz成功:{n_sz}'))
                        global_vars.lq.push(('交易线程-止损记录', 'Info', f'更新ppn成功:{ppn}'))
                        global_vars.lq.push(('交易线程-止损记录', 'Success', '一键止损成功'))
                else:
                    global_vars.lq.push(('交易线程-止损记录', 'Error', '一键止损失败'))

            # 统计盈亏情况
            profit = function.statistics_profit(o, trade_type, profit)

            # 整理需要更新到数据库的数据
            d = [
                formatted_now,  # 当前时间
                current_price,  # 当前价格
                before_price,  # 上一次价格
                p,  # 较昨天的涨跌幅
                last_p_p,  # 上一次价格和前一次价格的涨跌幅
                before_five_current_data_average,  # 上一次五个当前价格的平均值
                current_five_current_data_average,  # 当前五个当前价格的平均值
                before_mean_p,  # 用before_mean_p表示上一次主流货币当前价格标准化均值
                current_mean_p,  # 用current_mean_p表示当前主流币百分比变化平均值
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
                trade_type,  # 交易类型
                profit,  # 累计盈亏情况
                loss,  # 亏损累计值
            ]

            global_vars.r_d.append(d)  # 将数据添加到实时数据队列中

            # 更新上次前五个的当前价格平均值为当前前五个的当前价格平均值
            before_five_current_data_average = current_five_current_data_average
            # before_bidSz为当前bidSz,跟新before_askSz为当前askSz
            before_bidSz, before_askSz = current_bidSz, current_askSz
            # 更新上一周期的24小时交易量
            before_vol24h = current_vol24h
            # 更新上一周期btc,sol,eth,doge的价格标准化均值
            before_mean_p = current_mean_p

            # 更新随机休眠时间的区间，用于下次循环
            random_start, random_end = function.modulate_randomtime(random_start, random_end, before_price,

                                                                 current_price)
            # 更新上一周期价格
            before_price = current_price
            time.sleep(random_time)  # 休息一段时间,等待下一次循环

            # 及时保存重要参数
            try:
                function.save_parameter(long_place_downlimit, long_place_uplimit, short_place_downlimit,
                                        short_place_uplimit,
                                        l_c, s_c, u_p_1, u_p_2, u_p_3, u_p_4, d_p_1, d_p_2, d_p_3, d_p_4, n_sz, loss,
                                        profit)
                global_vars.lq.push(('交易线程-参数保存', 'Info', '保存重要参数成功'))
            except Exception as e:
                global_vars.lq.push(('交易线程-参数保存', 'Error', f'保存重要参数失败:{e}'))

            trade_type = 0  # 初始化交易类型
            # 刷新标准输出缓冲区，使其立即显示在控制台
            sys.stdout.flush()


        except Exception as e:
            if c < 3:
                global_vars.lq.push(('交易线程-错误记录', 'Error', f'出现异常错误: {e}，将重试'))
                c += 1
                time.sleep(10)  # 休眠10秒后重试

            else:  # 多次重新执行失败，发送邮件通知，退出程序，等待下一次计划程序的启动
                global_vars.s_finished_event = True  # 设置个事件,告知l,r线程，s线程将停止，l,s线程也应该停止

                send_email(sender=sender, receiver=receiver, password=sender_password,
                           subject='来自okx自动化策略程序的运行错误的提醒:',
                           content="发生在:strategy_manager_thread线程。\n"
                                   "错误位置：主while第一个try。\n"
                                   f"错误原因：{e}\n")
