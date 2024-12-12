"""
该模块包含了一系列函数，用于调整交易策略中的参数。具体功能包括：

- 调整随机休眠时间区间，以响应市场价格变动。
- 初始化交易策略中使用的动态参数，如价格变动区间计数器、随机时间区间界限、开仓上下限等。
- 更新不同价格变动区间的计数器。
- 调整开仓上下限，基于当前价格与上一次价格的比较结果。
- 在达到一定开仓次数后调整开仓上下限，以降低交易频率和风险。
- 保存和加载交易策略参数到文件。
"""
import time

from global_vars import lq

" 内置模块 "
import json

" 自定义模块 "
from myokx import MyOkx


# 根据市场价格变动调整随机休眠时间区间的函数
def modulate_randomtime(random_start: int, random_end: int, last_p: float, current_price: float) -> (int, int):
    """
    根据市场价格变动调整随机休眠时间区间。

    参数：
    - random_start: 随机休眠时间区间的左区间，表示休眠时间的最小值（秒）。
    - random_end: 随机休眠时间区间的右区间，表示休眠时间的最大值（秒）。
    - last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    - current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。

    返回：
    - 调整后的随机休眠时间区间（random_start, random_end）。
    """
    # 避免除以零的情况
    if last_p == 0:
        return random_start, random_end

    # 计算价格变动百分比
    last_p_p = abs((current_price - last_p) / last_p) if last_p != 0 else 0

    # 根据价格变动百分比调整随机休眠时间区间
    if last_p_p >= 0.01:
        # 变化太快，减少休眠时间以快速响应市场变化
        random_start, random_end = 2, 4
    elif 0.0015 < last_p_p:
        # 变化较快，适度减少休眠时间
        random_start, random_end = max(2, random_start - 45), min(100, random_end - 70)
    elif 0.001 < last_p_p:
        # 变化适中，略微减少休眠时间
        random_start, random_end = max(2, random_start - 20), min(100, random_end - 45)
    elif 0.0005 < last_p_p:
        # 变化较慢，略微增加休眠时间
        random_start, random_end = random_start + 1, random_end + 5
    elif last_p_p < 0.0005:
        # 变化很慢，增加休眠时间以减少交易频率
        random_start, random_end = random_start + 5, random_end + 20

    # 确保随机休眠时间区间的合理性
    random_start = max(2, min(45, random_start))  # random_start的最小值为2，最大值为45
    random_end = max(4, min(100, random_end))  # random_end的最小值为4，最大值为100

    # 确保random_start不大于random_end
    if random_end < random_start:
        random_start, random_end = random_end, random_start

    return random_start, random_end


# 初始化交易策略中使用的一系列动态参数的函数
def init_arguments(place_uplimit: float, place_downlimit: float) -> tuple:
    """
    初始化交易策略中使用的一系列动态参数。

    这些参数包括记录不同价格变动区间的次数计数器、随机时间区间的界限、开仓的上下限等。
    这些参数对于确定交易策略的行为至关重要，比如决定何时开仓、何时平仓等。

    参数：
    - place_uplimit: 用户设定的开仓涨幅上限。
    - place_downlimit: 用户设定的开仓跌幅下限。

    返回：
    - 一个包含初始化后的参数的元组，包括：
        u_p_1, d_p_1: 分别记录涨幅和跌幅在特定区间1的次数。
        u_p_2, d_p_2: 分别记录涨幅和跌幅在特定区间2的次数。
        u_p_3, d_p_3: 分别记录涨幅和跌幅在特定区间3的次数。
        u_p_4, d_p_4: 分别记录涨幅和跌幅在特定区间4的次数。
        random_start, random_end: 随机时间区间的左右界限。
        long_place_uplimit, long_place_downlimit: 开多仓的涨幅上下限。
        short_place_uplimit, short_place_downlimit: 开空仓的跌幅上下限。
        l_c, s_c: 开多仓和开空仓的次数计数器。
    """
    # 初始化记录不同价格变动区间的次数计数器
    u_p_1 = d_p_1 = u_p_2 = d_p_2 = u_p_3 = d_p_3 = u_p_4 = d_p_4 = 0

    # 初始化随机时间区间的界限
    random_start = 10  # 随机时间区间的最小值
    random_end = 20  # 随机时间区间的最大值

    # 初始化开仓的上下限
    long_place_uplimit = place_uplimit
    long_place_downlimit = place_downlimit
    short_place_uplimit = place_uplimit
    short_place_downlimit = place_downlimit

    # 初始化开多仓和开空仓的次数计数器
    l_c = 0  # 开多仓的次数计数器
    s_c = 0  # 开空仓的次数计数器

    return (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4,
            random_start, random_end,
            long_place_uplimit, long_place_downlimit,
            short_place_uplimit, short_place_downlimit,
            l_c, s_c)


# 根据当前价格变动更新不同价格变动区间的计数器的函数
def update_u_p_and_d_p(u_p_1: int, d_p_1: int, u_p_2: int, d_p_2: int, u_p_3: int, d_p_3: int, u_p_4: int, d_p_4: int,
                       p: float, l_s1: float, l_s2: float, l_s3: float, l_s4: float,
                       l_e1: float, l_e2: float, l_e3: float, l_e4: float,
                       s_s1: float, s_s2: float, s_s3: float, s_s4: float,
                       s_e1: float, s_e2: float, s_e3: float, s_e4: float) -> tuple:
    """
    根据当前价格变动更新不同价格变动区间的计数器。

    该函数根据当前的价格变动百分比（p），更新记录不同价格变动区间的次数计数器（u_p_1 到 u_p_4 和 d_p_1 到 d_p_4）。
    这些计数器用于跟踪市场在特定价格变动区间内的行为，这对于交易策略的决策过程至关重要。

    参数：
    - u_p_1 to u_p_4: 记录涨幅在特定区间1到4的次数。
    - d_p_1 to d_p_4: 记录跌幅在特定区间1到4的次数。
    - p: 当前的价格变动百分比。
    - l_s1 to l_s4: 涨幅区间1到4的左限。
    - l_e1 to l_e4: 涨幅区间1到4的右限。
    - s_s1 to s_s4: 跌幅区间1到4的左限。
    - s_e1 to s_e4: 跌幅区间1到4的右限。

    返回：
    - 更新后的各个价格变动区间的计数器 u_p_1 到 u_p_4 和 d_p_1 到 d_p_4。
    """
    # 更新涨幅区间计数器
    if l_s1 < p <= l_e1:
        u_p_1 += 1
    if l_s2 < p <= l_e2:
        u_p_2 += 1
    if l_s3 < p <= l_e3:
        u_p_3 += 1
    if l_s4 < p <= l_e4:
        u_p_4 += 1

    # 更新跌幅区间计数器
    if s_s1 < p <= s_e1:
        d_p_1 += 1
    if s_s2 < p <= s_e2:
        d_p_2 += 1
    if s_s3 < p <= s_e3:
        d_p_3 += 1
    if s_s4 < p <= s_e4:
        d_p_4 += 1

    return u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4


# 在开多仓成功后更新调整空仓的上下限的函数
def update_short_place_uplimit_and_short_place_downlimit(
        short_place_downlimit: float,
        short_place_uplimit: float,
        last_p: float,
        current_price: float,
        place_downlimit: float,
        place_uplimit: float
) -> tuple:
    """
    在开多仓成功后更新调整空仓的上下限。

    根据当前价格与上一次循环价格的比较结果，调整空仓的上下限，以反映市场的最新动态。
    这个调整是基于价格变动百分比（last_p_p），当价格变动百分比落在特定的区间内时，
    会相应地调整空仓的上下限，从而影响未来的开仓策略。

    参数：
    - short_place_downlimit: 当前空仓的下限，表示空仓可以触发的价格下限。
    - short_place_uplimit: 当前空仓的上限，表示空仓可以触发的价格上限。
    - last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    - current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。
    - place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的空仓下限。
    - place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的空仓上限。

    返回：
    - 调整后的空仓上下限（short_place_uplimit, short_place_downlimit）。
    """
    if last_p == 0:  # 避免除以零
        return short_place_downlimit, short_place_uplimit

    # 计算价格变动百分比
    last_p_p = (current_price - last_p) / last_p if last_p != 0 else 0

    # 根据价格变动百分比调整空仓上下限
    if 0 < last_p_p < 0.0005:  # 涨幅变化不高，发生反转的可能性最大
        short_place_downlimit -= 0.0005
        short_place_uplimit += 0.0005
    elif 0.0005 < last_p_p < 0.001:  # 涨幅大于0.0005，小于0.001，微调整
        short_place_downlimit -= 0.0002
        short_place_uplimit += 0.0002
    elif last_p_p > 0.001:  # 涨幅超过0.001，说明反转可能小
        short_place_downlimit += 0.0002
        short_place_uplimit -= 0.0002
    else:  # 价格下跌情况
        if last_p_p < -0.0005:
            short_place_downlimit += 0.0005
            short_place_uplimit -= 0.0005
        elif -0.0005 < last_p_p < 0:
            short_place_downlimit += 0.0002
            short_place_uplimit -= 0.0002
        elif last_p_p < -0.001:
            short_place_downlimit -= 0.0002
            short_place_uplimit += 0.0002

    # 确保调整后的上下限在用户设定的范围内
    short_place_downlimit = max(place_downlimit, min(short_place_downlimit, 0.0065))
    short_place_uplimit = max(place_uplimit, min(short_place_uplimit, 0.0065))

    return short_place_downlimit, short_place_uplimit


# 在开空仓成功后更新调整多仓的上下限的函数
def update_long_place_uplimit_and_long_place_downlimit(
        long_place_downlimit: float,
        long_place_uplimit: float,
        last_p: float,
        current_price: float,
        place_downlimit: float,
        place_uplimit: float
) -> tuple:
    """
    在开空仓成功后更新调整多仓的上下限。

    根据当前价格与上一次循环价格的比较结果，调整多仓的上下限，以反映市场的最新动态。
    这个调整是基于价格变动百分比（last_p_p），当价格变动百分比落在特定的区间内时，
    会相应地调整多仓的上下限，从而影响未来的开仓策略。

    参数：
    - long_place_downlimit: 当前多仓的下限，表示多仓可以触发的价格下限。
    - long_place_uplimit: 当前多仓的上限，表示多仓可以触发的价格上限。
    - last_p: 上一次循环的价格，用于与当前价格比较，计算价格变动百分比。
    - current_price: 当前的价格，用于与上一次循环的价格比较，计算价格变动百分比。
    - place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的多仓下限。
    - place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的多仓上限。

    返回：
    - 调整后的多仓上下限（long_place_uplimit, long_place_downlimit）。
    """
    if last_p == 0:  # 避免除以零
        return long_place_downlimit, long_place_uplimit

    # 计算价格变动百分比
    last_p_p = (current_price - last_p) / last_p if last_p != 0 else 0

    # 根据价格变动百分比调整多仓上下限
    if -0.0005 < last_p_p < 0.0005:  # 价格变动不大，微调多仓区间
        long_place_downlimit -= 0.0002 if last_p_p < 0 else 0.0002
        long_place_uplimit += 0.0002 if last_p_p > 0 else 0.0002
    elif last_p_p > 0.0005:  # 价格上涨超过0.0005，减少多仓区间
        long_place_downlimit += 0.0002
        long_place_uplimit -= 0.0002
    elif last_p_p < -0.0005:  # 价格下跌超过0.0005，增加多仓区间
        long_place_downlimit -= 0.0002
        long_place_uplimit += 0.0002

    # 确保调整后的上下限在用户设定的范围内
    long_place_downlimit = max(place_downlimit, min(long_place_downlimit, 0.0065))
    long_place_uplimit = max(place_uplimit, min(long_place_uplimit, 0.0065))

    return long_place_downlimit, long_place_uplimit


# 在开多仓次数达到一定阈值时调整多仓的上下限的函数
def update_long_place_downlimit_and_long_place_uplimit_for_the_l_c(
        long_place_downlimit: float,
        long_place_uplimit: float,
        place_downlimit: float,
        place_uplimit: float,
        l_c: int
) -> tuple:
    """
    在开多仓次数达到一定阈值时调整多仓的上下限。

    当开多仓的次数计数器（l_c）超过某个特定值时，意味着可能存在频繁的开多仓操作。
    为了降低交易频率和风险，此函数会调整多仓的上下限，使得未来的开多仓操作更加谨慎。

    参数：
    - long_place_downlimit: 当前多仓的下限，表示多仓可以触发的价格下限。
    - long_place_uplimit: 当前多仓的上限，表示多仓可以触发的价格上限。
    - place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的多仓下限。
    - place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的多仓上限。
    - l_c: 开多仓的次数计数器，用于确定是否需要调整多仓的上下限。

    返回：
    - 调整后的多仓上下限（long_place_downlimit, long_place_uplimit）。
    """
    # 定义调整步长
    adjustment_step = 0.0001

    # 如果开多仓次数超过一定阈值，逐步增加多仓上下限，减少交易频率
    if l_c > 0:  # 假设超过0次就考虑调整
        for _ in range(l_c):
            long_place_downlimit += adjustment_step
            long_place_uplimit -= adjustment_step

    # 确保调整后的上下限在用户设定的范围内
    long_place_downlimit = max(place_downlimit, min(long_place_downlimit, 0.0065))
    long_place_uplimit = max(place_uplimit, min(long_place_uplimit, 0.0065))

    return long_place_downlimit, long_place_uplimit


# 在开空仓次数达到一定阈值时调整空仓的上下限的函数
def update_short_place_downlimit_and_short_place_uplimit_for_the_s_c(
        short_place_downlimit: float,
        short_place_uplimit: float,
        place_downlimit: float,
        place_uplimit: float,
        s_c: int
) -> tuple:
    """
    在开空仓次数达到一定阈值时调整空仓的上下限。

    当开空仓的次数计数器（s_c）超过某个特定值时，意味着可能存在频繁的开空仓操作。
    为了降低交易频率和风险，此函数会调整空仓的上下限，使得未来的开空仓操作更加谨慎。

    参数：
    - short_place_downlimit: 当前空仓的下限，表示空仓可以触发的价格下限。
    - short_place_uplimit: 当前空仓的上限，表示空仓可以触发的价格上限。
    - place_downlimit: 用户设定的开仓跌幅下限，用于确定调整后的空仓下限。
    - place_uplimit: 用户设定的开仓涨幅上限，用于确定调整后的空仓上限。
    - s_c: 开空仓的次数计数器，用于确定是否需要调整空仓的上下限。

    返回：
    - 调整后的空仓上下限（short_place_downlimit, short_place_uplimit）。
    """
    # 定义调整步长
    adjustment_step = 0.0001

    # 如果开空仓次数超过一定阈值，逐步增加空仓上下限，减少交易频率
    if s_c > 0:  # 假设超过0次就考虑调整
        for _ in range(s_c):
            short_place_downlimit += adjustment_step
            short_place_uplimit -= adjustment_step

    # 确保调整后的上下限在用户设定的范围内
    short_place_downlimit = max(place_downlimit, min(short_place_downlimit, 0.0025))
    short_place_uplimit = max(place_uplimit, min(short_place_uplimit, 0.0065))

    return short_place_downlimit, short_place_uplimit


# 保存当前的动态参数到文件的函数
def save_parameter(long_place_downlimit: float, long_place_uplimit: float,
                   short_place_downlimit: float, short_place_uplimit: float,
                   l_c: int, s_c: int, u_p_1: int, u_p_2: int, u_p_3: int, u_p_4: int,
                   d_p_1: int, d_p_2: int, d_p_3: int, d_p_4: int, n_sz: int, loss: float, profit: float) -> None:
    """
    保存当前的动态参数到文件。

    这些参数包括开仓上下限、涨跌幅区间计数器、随机时间区间等，它们会被保存到一个JSON文件中，
    以便在下一次程序启动时能够加载这些参数，从而保持策略的连续性和状态的持久性。

    参数：
    - long_place_downlimit: 多头开仓的下限价格变动百分比。
    - long_place_uplimit: 多头开仓的上限价格变动百分比。
    - short_place_downlimit: 空头开仓的下限价格变动百分比。
    - short_place_uplimit: 空头开仓的上限价格变动百分比。
    - l_c: 多头开仓次数计数器。
    - s_c: 空头开仓次数计数器。
    - u_p_1 to u_p_4: 涨幅区间1到4的计数器。
    - d_p_1 to d_p_4: 跌幅区间1到4的计数器。
    - n_sz: 实际的minSz整数倍。
    - loss: 累计亏损金额(USDT)
    - profit: 累计盈利金额(USDT)
    返回：
    - 无返回值，函数执行后会将参数保存到文件中。
    """
    # 构建要保存的数据字典
    data = {
        'long_place_downlimit': long_place_downlimit,
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
        'n_sz': n_sz,
        'loss': loss,
        'profit': profit
    }

    # 将数据字典转换为JSON字符串并保存到文件
    with open('parameter.txt', 'w') as f:
        f.write(json.dumps(data, indent=4))  # 使用indent参数美化输出


# 从文件中加载动态参数的函数
def load_parameter() -> tuple | None:
    """
    从文件中加载动态参数。

    这些参数包括开仓上下限、涨跌幅区间计数器、随机时间区间等，它们被保存在一个JSON文件中。
    该函数将从文件中读取这些参数，并返回它们，以便在程序启动时初始化策略状态。

    参数：
    - 无

    返回：
    - 一个包含加载的参数的元组，包括：
        long_place_downlimit, long_place_uplimit: 多仓的上下限价格变动百分比。
        short_place_downlimit, short_place_uplimit: 空仓的上下限价格变动百分比。
        l_c, s_c: 分别为开多仓和开空仓的次数计数器。
        u_p_1 to u_p_4: 涨幅区间1到4的计数器。
        d_p_1 to d_p_4: 跌幅区间1到4的计数器。
        n_sz: 实际的minSz整数倍。
    """
    try:
        # 打开文件并加载JSON数据
        with open('parameter.txt', 'r') as f:
            data = json.load(f)

        # 提取参数并返回
        return (
            data['long_place_downlimit'],
            data['long_place_uplimit'],
            data['short_place_downlimit'],
            data['short_place_uplimit'],
            data['l_c'],
            data['s_c'],
            data['u_p_1'],
            data['u_p_2'],
            data['u_p_3'],
            data['u_p_4'],
            data['d_p_1'],
            data['d_p_2'],
            data['d_p_3'],
            data['d_p_4'],
            data['n_sz'],
            data['loss'],
            data['profit']
        )
    except FileNotFoundError:
        # 如果文件不存在，返回默认值或抛出异常
        print("参数文件未找到")
        return None
    except json.JSONDecodeError:
        # 如果JSON解析失败，返回默认值或抛出异常
        print("参数文件格式错误")
        return None


# 执行止盈操作，并在操作后重新初始化相关参数的函数
def take_progit(o: MyOkx, instId: str, leverage: int, place_uplimit: float, place_downlimit: float) -> tuple | None:
    """
    执行止盈操作，并在操作后重新初始化相关参数。

    当触发止盈条件时，此函数会被调用来平掉当前持有的仓位，并根据市场的最新状态重新设置交易参数，
    以准备下一次的交易决策。

    参数：
    - o: MyOkx类的实例，用于与OKX交易所API进行交互。
    - instId: 交易对的标识符，例如'ETH-USDT-SWAP'。
    - leverage: 交易使用的杠杆倍数。
    - place_uplimit: 开仓的涨幅上限。
    - place_downlimit: 开仓的跌幅下限。

    返回：
    - 如果止盈操作成功，返回更新后的参数集合，包括涨跌幅区间计数器和随机时间区间等；
    - 如果失败，则返回None。
    """
    try:
        # 执行止盈操作，平掉所有仓位
        close_positions_re = o.close_positions(instId=instId, leverage=leverage, ordType='market', tdMode='cross',
                                               limit_uplRatio=0)

        # 检查止盈操作是否成功
        if close_positions_re == 1:
            lq.push(('止盈记录', 'Success', '一键止盈成功'))
            # 止盈操作成功，重新初始化相关参数
            # 这里假设init_arguments函数用于初始化参数
            (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4,
             random_start, random_end,
             long_place_uplimit, long_place_downlimit,
             short_place_uplimit, short_place_downlimit,
             l_c, s_c) = init_arguments(place_uplimit, place_downlimit)

            # 返回更新后的参数
            return (u_p_1, d_p_1, u_p_2, d_p_2, u_p_3, d_p_3, u_p_4, d_p_4,
                    random_start, random_end,
                    long_place_uplimit, long_place_downlimit,
                    short_place_uplimit, short_place_downlimit,
                    l_c, s_c)
        else:
            # 止盈操作失败
            lq.push(('止盈记录', 'Error', '一键止盈失败'))
            return None
    except Exception as e:
        # 处理可能出现的异常
        print(f"止盈操作异常: {e}")
        return None


def statistics_profit(o: MyOkx, trade_type: int, profit: float) -> float:
    """
    这个函数会根据交易类型来统计累计盈利情况
    :param o: MyOkx类的实例，用于与OKX交易所API进行交互。
    :param trade_type: 发生的交易类型，这里只有-2，2，3值时，才会统计
    :param profit: 累计盈亏情况
    :return: 返回累计盈亏情况
    """
    if trade_type in [-1, 1, 0]: return profit  # 没有发生止盈止损操作，直接返回

    if trade_type == 3:  # 说明交易类型是止损平仓
        while True:
            realizedPnl = float(o.get_positions_history()['realizedPnl'])  # 获取亏损金额
            if realizedPnl > 0:  # 如果金额大于0，就继续等待,可能刚刚平仓的仓位信息还没有更新
                time.sleep(3)
            else:
                break
    else:
        while True:  # 说明交易类型是止盈平仓
            realizedPnl = float(o.get_positions_history()['realizedPnl'])  # 获取亏损金额
            if realizedPnl < 0:  # 如果金额大于0，就继续等待，可能刚刚平仓的仓位信息还没有更新
                time.sleep(3)
            else:
                break

    return profit + realizedPnl
