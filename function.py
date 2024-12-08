"""
这个模块包含了一系列的函数，用于调整交易策略中的参数。具体功能包括：

调整随机休眠时间区间，以响应市场价格变动。
初始化交易策略中使用的动态参数，如价格变动区间计数器、随机时间区间界限、开仓上下限等。
更新不同价格变动区间的计数器。
调整开仓上下限，基于当前价格与上一次价格的比较结果。
在达到一定开仓次数后调整开仓上下限，以降低交易频率和风险。
保存和加载交易策略参数到文件。
@Time: 2024/12/7 9:45
@Author: ysh
@File: function.py
"""

" 内置模块 "
import json

" 自定义模块 "
from myokx import MyOkx


# 根据市场价格变动调整随机休眠时间区间的函数
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


# 初始化交易策略中使用的一系列动态参数的函数
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


# 根据当前价格变动更新不同价格变动区间的计数器的函数
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


# 在开多仓成功后更新调整空仓的上下限的函数
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


# 在开空仓成功后更新调整多仓的上下限的函数
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


# 在开多仓次数达到一定阈值时调整多仓的上下限的函数
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


# 在开空仓次数达到一定阈值时调整空仓的上下限的函数
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


# 保存当前的动态参数到文件的函数
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


# 从文件中加载动态参数的函数
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
                data['d_p_3'], data['d_p_4'], data['n_sz'])


# 执行止盈操作，并在操作后重新初始化相关参数的函数
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
