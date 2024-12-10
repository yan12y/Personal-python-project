"""
该模块定义了交易策略中使用的信号生成函数，用于确定开多仓和开空仓的时机。
"""

from predict_model import data_to_df
import global_vars


def go_long_signal(long_place_downlimit: float, long_place_uplimit: float, p: float, last_p_p: float,
                   before_five_current_data_average: float,
                   current_five_current_data_average: float,
                   before_mean_normalized: float,
                   current_mean_normalized: float,
                   l_c: int, l_c_limit: int, before_bidSz: float, current_bidSz: float,
                   before_vol24h: float, current_vol24h: float) -> bool:
    """
    生成多头（买入）信号的函数。

    根据当前价格与前一日收盘价的变动百分比、近期价格平均值的变化、多头开仓计数器以及买单深度的变化来判断是否应该开多仓。

    :param long_place_downlimit: 多头开仓价格变动的下限。
    :param long_place_uplimit: 多头开仓价格变动的上限。
    :param p: 当前价格与前一日收盘价的变动百分比。
    :param last_p_p: （当前价格 - 上一次价格）/ 上一次价格
    :param before_five_current_data_average: 前五个周期的当前价格平均值。
    :param current_five_current_data_average: 当前五个周期的当前价格平均值。
    :param current_mean_normalized: 上一次btc,sol,eth,doge的价格标准化均值
    :param before_mean_normalized: 当前btc,sol,eth,doge的价格标准化均值
    :param l_c: 多头开仓计数器，用于跟踪多头开仓的次数。
    :param l_c_limit: 这是开多仓的最多次数
    :param before_bidSz: 前一次的买单深度（bid size）。
    :param current_bidSz: 当前的买单深度（bid size）。
    :param before_vol24h: 前一次的24小时交易量
    :param current_vol24h: 当前的24小时交易量
    :return: 如果满足开多仓条件，返回True；否则，返回False。
    """
    if (long_place_downlimit < p < long_place_uplimit and
            float(before_five_current_data_average) <= float(current_five_current_data_average) and
            float(before_mean_normalized) <= float(current_mean_normalized) and
            l_c <= l_c_limit and
            float(before_bidSz) < float(current_bidSz) and
            before_vol24h < current_vol24h and
            last_p_p > 0):

        return True
    else:
        return False


def go_short_signal(short_place_downlimit: float, short_place_uplimit: float, p: float, last_p_p: float,
                    before_five_current_data_average: float,
                    current_five_current_data_average: float,
                    before_mean_normalized: float,
                    current_mean_normalized: float,
                    s_c: int, s_c_limit: int, before_askSz: float, current_askSz: float,
                    before_vol24h: float, current_vol24h: float) -> bool:
    """
    生成空头（卖出）信号的函数。

    根据当前价格与前一日收盘价的变动百分比、近期价格平均值的变化、空头开仓计数器以及卖单深度的变化来判断是否应该开空仓。
    btc,sol,eth,doge是主流币种，它们的价格变化反映了市场整体走向，
    btc,sol,eth,doge的价格标准化均值，可以消除大价格币种忽略小价格币种，影响判市场走向的判断。从而保证判断市场走向是由它们整体共同判断。

    :param short_place_downlimit: 空头开仓价格变动的下限。
    :param last_p_p: （当前价格 - 上一次价格）/ 上一次价格
    :param short_place_uplimit: 空头开仓价格变动的上限。
    :param p: 当前价格与前一日收盘价的变动百分比。
    :param before_five_current_data_average: 前五个周期的当前价格平均值。
    :param current_five_current_data_average: 当前五个周期的当前价格平均值。
    :param current_mean_normalized: 上一次btc,sol,eth,doge的价格标准化均值
    :param before_mean_normalized: 当前btc,sol,eth,doge的价格标准化均值
    :param s_c: 空头开仓计数器，用于跟踪空头开仓的次数。
    :param s_c_limit: 这是开空仓的最多次数
    :param before_askSz: 前一次的卖单深度（ask size）。
    :param current_askSz: 当前的卖单深度（ask size）。
    :param before_vol24h: 前一次的24小时交易量
    :param current_vol24h: 当前的24小时交易量
    :return: 如果满足开空仓条件，返回True；否则，返回False。
    """
    if (-short_place_downlimit > p > -short_place_uplimit and
            float(before_five_current_data_average) >= float(current_five_current_data_average) and
            float(before_mean_normalized) >= float(current_mean_normalized) and
            s_c <= s_c_limit and
            float(before_askSz) <= float(current_askSz) and
            before_vol24h <= current_vol24h and
            last_p_p < 0):
        return True
    else:
        return False


def predict(current_price: float,
            last_price: float,
            before_five_current_data_average: float,
            current_five_current_data_average: float,
            before_mean_normalized: float,
            current_mean_normalized: float,
            before_bidSz: float,
            current_bidSz: float,
            before_askSz: float,
            current_askSz: float,
            before_vol24h: float,
            current_vol24h: float) -> bool:
    """
    使用训练好的模型预测交易是否盈利。

    参数：
    - current_price: float, 当前价格。
    - last_price: float, 上一次价格。
    - before_five_current_data_average: float, 前五个周期的当前价格平均值。
    - current_five_current_data_average: float, 当前五个周期的当前价格平均值。
    - before_mean_normalized: float, 上一次主流货币的价格标准化均值。
    - current_mean_normalized: float, 当前主流货币的价格标准化均值。
    - before_bidSz: float, 前一次的买单深度（bid size）。
    - current_bidSz: float, 当前的买单深度（bid size）。
    - before_askSz: float, 前一次的卖单深度（ask size）。
    - current_askSz: float, 当前的卖单深度（ask size）。
    - before_vol24h: float, 前一次的24小时交易量。
    - current_vol24h: float, 当前的24小时交易量。

    返回：
    - bool, 如果预测盈利，返回True；否则，返回False。
    """
    # 检查是否有可用的最佳模型和未经标准化的特征数据集
    if global_vars.best_model is None or global_vars.attr_df is None:
        # 如果没有可用模型或数据，无法进行预测，返回True以保守起见
        return True

    # 将当前数据转换为DataFrame，并进行标准化处理
    new_d = data_to_df(global_vars.attr_df,
                       current_price, last_price,
                       current_five_current_data_average, before_five_current_data_average,
                       current_mean_normalized, before_mean_normalized,
                       current_bidSz, before_bidSz,
                       current_askSz, before_askSz,
                       current_vol24h, before_vol24h)

    # 使用最佳模型进行预测,返回预测结果，True表示预测盈利，False表示预测亏损
    if global_vars.best_model.predict(new_d)[0] == 1:
        return True
    else:
        return False
