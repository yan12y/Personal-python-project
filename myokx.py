"""
该模块定义了一个MyOkx类，封装了与OKX交易所API交互的接口。具体功能包括：

- 获取账户信息。
- 设置杠杆倍数。
- 下单交易。
- 获取仓位信息。
- 获取历史K线数据。
- 平仓操作。
"""


# 内置模块
import requests
import json
from datetime import datetime
import time

# 第三方模块
from okx.Account import AccountAPI
from okx.MarketData import MarketAPI
from okx.Trade import TradeAPI

import global_vars


def get_instId_lotsz(instrument_type, instrument_id):
    """
    获取instId对应的最小下单倍数
    :param instrument_type: 交易类型，如'SWAP', 'FUTURES'等
    :param instrument_id: 交易id 如：BTC-USDT
    :return:
    """
    url = "https://www.okx.com/api/v5/public/instruments"
    params = {
        'instType': instrument_type,
        'instId': instrument_id
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == '0':
            return data['data'][0]['lotSz']
        else:
            return None
    else:
        return None


def get_ticker_last_price(instId: str) -> tuple | None:
    """
    获取交易币对最近的市价信息
    :param instId: 交易类型
    :return: 返回交易对的所有信息，交易对的最新价格信息，当前最新价格较昨收盘价的变化百分比变化
    """
    url = 'https://www.okx.com/api/v5/market/ticker'
    params = {
        'instId': instId,
    }
    res = requests.get(url=url, params=params)
    if res.status_code == 200:
        data1 = json.dumps(res.json(), indent=4)
        data1 = json.loads(data1)
        data = data1['data'][0]
        p = (float(data['last']) - float(data['sodUtc8'])) / float(data['sodUtc8'])
        return data1['data'][0], float(data['last']), p
    else:
        return None


class MyOkx:
    """
    注意：访问Okx需要连接vpn。这里面的大部分方法都访问到了Okx。
    这个类封装了Okx的接口，你可以通过这个类来获取账户信息，下单，获取K线数据等。
    """

    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None):
        """
        实例化这个类时，请你提供api_key，secret_key，passphrase这些参数，这些参数中：api_key，secret_key
        是你在Okx自己的账户上申请api成功后，Okx官方提供给你的参数。passphrase是你在申请api时自己设置的。如果你不提供这些参数，
        需要操作账户信息的所有方法将直接返回None。
        :param api_key:
        :param secret_key:
        :param passphrase:
        """
        self.flag = "0"  # 实盘:0 , 模拟盘：1
        if api_key is None or secret_key is None or passphrase is None:
            self.account = None
            self.trade_api = None
            self.market_api = None
        else:
            self.account = AccountAPI(api_key, secret_key, passphrase, flag=self.flag, debug=False)
            self.trade_api = TradeAPI(api_key, secret_key, passphrase, flag=self.flag, debug=False)
            self.market_api = MarketAPI(api_key, secret_key, passphrase, flag=self.flag, debug=False)

    def get_account_info(self):
        """
        注意：这个需要账户信息，请你实例化对象是提供对应的api参数。
        这个方法会获取账户信息。如果你实例化这个类时，所提供的参数正确，而且网络可用（访问Okx需要连接vpn），
        那么会返回账户信息。如果网络可用，但是因为某种原因(code值不是0）时，返回空。
        :return:set类型的数据,里面的元素类型是字典，或者None。
        """
        if self.account is None:
            return None

        data = self.account.get_account_balance()
        if data and data['code'] == '0':
            updated_time_str = data['data'][0]['details'][0]['uTime']  # 获取时间戳字符串

            # 尝试将其转换为毫秒级时间戳
            try:
                # 如果时间戳是一个数字字符串，将其转换为整数
                updated_time_ms = int(updated_time_str)

                # 将毫秒级时间戳转换为秒级时间戳
                updated_time_seconds = int(updated_time_ms / 1000)

                # 将秒级时间戳转换为日期时间对象
                updated_time = datetime.utcfromtimestamp(updated_time_seconds)  # 转换为日期时间对象

                # 将转换后的时间添加到数据字典中
                data['data'][0]['details'][0]['uTime'] = updated_time
                return data
            except ValueError:
                # 如果时间戳不是一个数字字符串，则可能是其他格式，需要进一步处理
                return None
        return None

    def set_leverage(self, instId: str, mgnMode: str, leverage: int):
        """
        注意：这个需要账户信息，请你实例化对象是提供对应的api参数。
        这个方法用来设置杠杆倍数的。
        :param instId: 合约代码，如 "BTC-USDT-SWAP"。
        :param mgnMode: 保证金模式，如 "cross" 或 "isolated"。
                       - "cross": 全仓保证金模式。
                       - "isolated": 逐仓保证金模式。
        :param leverage: 杠杆倍数。
        :return: 返回设置杠杆倍数。或者None
        """
        if self.account is None:
            return None

        params = {
            'instId': instId,
            'mgnMode': mgnMode,
            'lever': leverage
        }
        re = self.account.set_leverage(**params)
        if re and re['code'] == '0':
            return int(re['data'][0]['lever'])
        return None

    def place_agreement_order(self, instId: str, tdMode: str, side: str, ordType: str, lever: int, sz: int = 0,

                              ccy: str = 'USDT', **kwargs):
        """
        注意：这个需要账户信息，请你实例化对象是提供对应的api参数。
        这个方法用来进行合约下单的。也就是说你的instId参数只能为：xx-xx-SWAP,每一次都以最小的下单

        :param instId: 合约代码，如 "BTC-USDT-SWAP"。
        :param tdMode: 交易模式，如 "cross" 或 "isolated"。
                       - "cross": 使用整个账户的保证金来支持交易。
                       - "isolated": 使用特定头寸的保证金来支持交易。
        :param side: 交易方向，如 "buy" 或 "sell"。
                     - "buy": 买入。
                     - "sell": 卖出。
        :param ordType: 订单类型，如 "limit" 或 "market"。
                        - "limit": 限价订单。
                        - "market": 市价订单。
        :param lever: 杠杆倍数
        :param sz : minSz的整数倍
        :param ccy: 保证金货币，如 "USDT"。
                    指定保证金使用的货币种类。
        :param kwargs: 可选参数，可以包括但不限于以下参数：
            - clOrdId (str): 客户订单ID，用户自定义的订单ID，用于跟踪订单。
            - tag (str): 订单标签，可以用于标记订单的附加信息。
            - posSide (str): 头寸方向，如 "long" 或 "short"。
                              - "long": 多头。
                              - "short": 空头。
            - px (str): 价格，仅限于限价订单。
                         对于限价订单，需要指定价格。
            - reduceOnly (str): 减仓标志。
                                 - "true": 减少现有头寸。
                                 - "false": 增加或开新头寸。
            - tgtCcy (str): 目标货币，用于指定保证金使用的货币种类。
            - tpTriggerPx (str): 止盈触发价格。
                                 触发止盈的价格。
            - tpOrdPx (str): 止盈订单价格。
                             止盈订单的执行价格。
            - slTriggerPx (str): 止损触发价格。
                                 触发止损的价格。
            - slOrdPx (str): 止损订单价格。
                             止损订单的执行价格。
            - tpTriggerPxType (str): 止盈触发类型，如 "last", "index", "mark"。
            - slTriggerPxType (str): 止损触发类型，如 "last", "index", "mark"。
            - quickMgnType (str): 快速保证金类型。
                                   用于快速保证金类型的设置。
            - stpId (str): STP组ID，用于识别特定的STP组。
            - stpMode (str): STP模式，如 "partial_close", "close_first", "close_last"。
            - attachAlgoOrds (list): 附加算法订单，如果有的话，可以附加算法订单。
        :return: 返回订单信息。或者None
        """
        if self.trade_api is None:
            return None

        # 设置杠杆倍数
        self.set_leverage(instId, tdMode, lever)
        # 获取最小下单量的倍数
        minSz = float(get_instId_lotsz(instrument_type='SWAP', instrument_id=instId))
        global_vars.minSz = minSz

        sz = float(minSz * sz)

        if sz == 0 or sz <= minSz:
            sz = minSz

        # sz保留一位小数
        sz = round(sz, 1)

        params = {
            "instId": instId,
            "tdMode": tdMode,
            "ordType": ordType,
            "ccy": ccy,
            "side": side,  # 根据需要设置为buy或sell
            "sz": str(sz)  # 假设你需要根据position_nums和lever来计算订单大小
        }
        data = self.trade_api.place_order(**params, **kwargs)
        print(data)
        if data['code'] != '0':
            return data, 0
        else:
            return data, sz

    def get_positions(self):
        """
        注意：这个需要账户信息，请你实例化对象是提供对应的api参数。
        获取所有仓位信息
        :return: 返回所有仓位的信息,或者None
        """
        if self.account is None:
            return None

        data = json.dumps(self.account.get_positions(), indent=4)
        data = json.loads(data)['data']
        return data

    def get_closing_prices(self, start_date: str, end_date: str, instId: str):
        """
        注意：这方法返回的数据为从00:00(UTC+8)开始计算的数据
        这个方法会返回交易对的对应时间段的历史日K线数据现数据,不包含开始时间和结束时间的日数据
        :param:start_date:开始时间的时间格式为：%Y-%m-%d %H:%M:%S,假设你开始时间2018-10-01的数据，
        那么这个参数就是2018-10-01。
        :param:end_date:结束时间的时间格式同开始时间一样。
        :param:instId:交易币对
        :return:返回一个包含数组的数组数据，或者None
        """
        marketDataAPI = MarketAPI(flag=self.flag, debug=False)

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")  # 将字符串转换为时间对象
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        end_dateTs = int(end_date_obj.timestamp() * 1000)  # 这是结束时间 ，将秒级时间戳转换为毫秒级时间戳
        start_dateTs = int(start_date_obj.timestamp() * 1000)  # 这是开始时间

        result = marketDataAPI.get_history_candlesticks(
            instId=instId,
            after=end_dateTs,
            before=start_dateTs,
            bar='1D',
        )  # 获取历史K线数据

        if result is not None and result['code'] == '0' and result['data'] != []:
            # 时间戳转换为日期格式
            data = result['data']

            # 时间戳转为日期
            for item in data:
                item[0] = datetime.fromtimestamp(int(item[0]) / 1000).strftime('%Y-%m-%d')
            return data
        else:
            return None

    def close_positions(self, instId=None, leverage=10, ordType='market', tdMode='cross', limit_uplRatio: float = -1,
                        ccy: str = 'USDT'):
        """
        一键平仓，平掉当前持仓。如果提供了 instId 参数，仅平掉该合约的持仓。
        :param instId: 合约代码，如果为 None 则不进行任何操作
        :param leverage: 杠杆倍数
        :param ordType: 订单类型，限价单或市价单
        :param tdMode: 交易模式，例如 'cross' 或 'isolated'
        :param limit_uplRatio: 当limit_uplRatio为负且小于此值时进行的止损平仓；当limit_uplRatio为0时用于相应仓位的止盈平仓
        :param ccy: 保证金货币，如 "USDT"。
            指定保证金使用的货币种类。
        :return: 返回平仓操作的结果，或者 None
        """
        if self.account is None or self.trade_api is None:
            return None

            # 检查 instId，若为 None 则不进行任何操作
        if instId is None:
            return None

        positions = self.get_positions()  # 获取当前所有仓位信息
        if positions is []:
            return None  # 没有持仓，返回 None

        for position in positions:
            # 如果指定了 instId，则只处理该合约
            if position['instId'] != instId:
                continue

            pos = float(position['pos'])  # 当前持仓量
            uplRatio = float(position['uplRatio'])  # 获取未实现利润比例

            if pos > 0:
                # 当前是多头仓位，平仓操作为卖出
                side = 'sell'
            elif pos < 0:
                # 当前是空头仓位，平仓操作为买入
                side = 'buy'
            else:
                continue  # 如果持仓量为0，则跳过

            # 设置杠杆
            self.set_leverage(instId, tdMode, leverage)
            # 进行平仓条件检查
            if uplRatio < 0 and uplRatio < limit_uplRatio:
                # 使用 self.trade_api.place_order 进行下单
                result = self.trade_api.place_order(
                    instId=position['instId'],
                    tdMode=tdMode,
                    side=side,
                    ordType=ordType,
                    ccy=ccy,
                    sz=str(abs(pos)),  # 使用绝对值作为下单数量
                )
                if result['code'] == '0':  # 执行操作失败
                    return 1
                else:
                    return -1

            elif limit_uplRatio == 0 and pos < 0:  # 空止盈
                result = self.trade_api.place_order(
                    instId=position['instId'],
                    tdMode=tdMode,
                    side='buy',
                    ordType=ordType,
                    ccy=ccy,
                    sz=str(abs(pos)),  # 使用绝对值作为下单数量
                )
                if result['code'] == '0':
                    return 1
                else:
                    return -1

            elif limit_uplRatio == 0 and pos > 0:  # 多止盈
                result = self.trade_api.place_order(
                    instId=position['instId'],
                    tdMode=tdMode,
                    side='sell',
                    ordType=ordType,
                    ccy=ccy,
                    sz=str(abs(pos)),  # 使用绝对值作为下单数量
                )
                if result['code'] == '0':
                    return 1
                else:
                    return -1

        return None  # 如果没有进行任何平仓操作，返回 None

    def get_positions_history(self,instType='SWAP',instId='ETH-USDT-SWAP'):
        """
        获取历史持仓信息
        :param instType:   交易品种类型
        :param instId:   交易品种
        :return:  返回最新的一条历史仓位记录
        """
        # 获取历史持仓信息
        time.sleep(15)
        positions_history = self.account.get_positions_history(instType=instType, instId=instId,limit=1)
        return positions_history['data'][0]