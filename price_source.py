# -*- coding: utf-8 -*-
import threading
import traceback
from decimal import Decimal
from bs4 import BeautifulSoup

import redis
import sys
import time
import json

from utils import get_real_price, get_source_type, set_current_price, get_response, get_close_price

# 各个请求地址的url
url1 = ''
url2 = ''
url3 = ''
url4 = ''
url5 = ''
url6 = ''
url7 = ''
url8 = ''
url9 = ''
url10 = ''
url11 = ''
url12 = ''


REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ''


def get_redis_cli():
    try:
        pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT,
                                    db=REDIS_DB, password=REDIS_PASSWORD)

        redis_cli = redis.Redis(connection_pool=pool)
        redis_cli.set("test", "test")
        return redis_cli
    except Exception, e:
        # todo 报警
        print >> sys.stderr, u'redis connection error with {}'.format(e.message)
        print >> sys.stderr, traceback.print_exc()
        # redis_cli = None
        raise Exception, e


def get_source_gold_price(num):
    """
    根据序号(num)获取对应url的黄金价格
    :param num:
    :return: price
    """
    price = 0
    headers = None
    if not num:
        return price
    elif num == 3:
        headers = {'referer': 'http://quote.go24k.com:8080/quoteshowbigshxhhq.asp'}
    elif num in (4, 9):
        headers = {'referer': 'http://www.chngc.net/'}

    url = eval('url' + str(num))
    ret = get_response(url, headers=headers)

    if ret.get('status_code') == 200:
        try:
            if num in (1, 2, 4, 7, 8, 9):
                res_data = json.loads(ret.get('text'))
            elif num in (5, 6, 10, 11):
                res_data = BeautifulSoup(ret.get('text'), 'lxml')
            else:
                res_data = ret.get('text')
        except:
            res_data = BeautifulSoup(ret.get('text'), 'lxml')

        try:
            if num == 1:
                price = res_data['results'][0]['price']
            elif num == 2:
                price = res_data['Data']['Table'][1]['CurrentPrice']
            elif num == 3:
                price = res_data.split(",newPrice:'")[1].split("',open:")[0]
            elif num == 4:
                price = res_data['List'][3]['TradePrice']
            elif num == 5:
                price = res_data.div.find_all('tr')[1].find_all('td')[2].text.strip()
            elif num == 6:
                price = res_data.table.find_all('tr')[-1].find_all('td')[1].text.strip()

            elif num == 7:
                price = res_data['results'][0]['price']
            elif num == 8:
                price = res_data['Data']['Table1'][2]['CustomerSell']
            elif num == 9:
                price = res_data['List'][0]['TradePrice']
            elif num == 10:
                price = res_data.find_all(id="TABLE1")[0].find_all('tr')[5].find_all('td')[2].text.strip()
            elif num == 11:
                price = res_data.find_all('span')[3].text.strip()
        except Exception, e:
            print >> sys.stderr, u'数据源:{} 出现异常: {}'.format(num, e.message)
    else:
        # 在请求里面报警
        pass

    return price


class BaseThread(threading.Thread):

    # TODO
    # 把锁 和 sleep 参数都放到装饰器里

    def __init__(self, thread_name, lock, num):

        self.redis_cli = get_redis_cli()
        self._lock = lock
        self.num = num
        # self.daemon = True

        threading.Thread.__init__(self, name=thread_name)

    def _set(self, order, price='0'):
        try:
            float(price)
        except:
            price = filter(lambda ch: ch in '0123456789.', price)

        self.redis_cli.hset('gold_price_source_{}'.format(order), 'price', price)
        # 在request 的时候已经判断是否报警
        # if float(price) == 0:
        #     # to do 报警
        #     print >> sys.stderr, u'source {} 请求失败'.format(order)

    def run(self):
        pass


class SourcePrice(BaseThread):
    """
    获取不同源的金价并存储
    """
    def run(self):
        while True:

            # 加锁会慢一秒多, 取消了
            # self._lock.acquire(1)
            price = get_source_gold_price(self.num)  # 获取源序号对应url的金价
            try:
                self._set(self.num, price)  # 存入外源金价
            except Exception, e:
                print >> sys.stderr, e.message
            # self._lock.release()
            time.sleep(10)


class RealPrice(BaseThread):
    """
    这个实时获取最新金价去设置为当前金价
    """

    def run(self):
        while True:
            redis_cli = self.redis_cli
            adjust_info = redis_cli.hgetall('gold_price_settings')

            # 特殊调价
            if adjust_info.get('type') == 'special':
                check_price2 = redis_cli.hget('python_gold_price', 'buy_price')
                current_price2 = Decimal(adjust_info.get('adjust_price'))
                check_price2 = current_price2 if not check_price2 else current_price2
            # 普通调价
            elif adjust_info.get('type') == 'normal':
                current_price = Decimal(redis_cli.hget('python_gold_price', 'buy_price'))
                check_price = redis_cli.hget('gold_price_settings', 'adjust_price')
                print current_price, check_price
                # 获取需要更新进去的价格
                check_price2, current_price2 = get_real_price(redis_cli, current_price, check_price, True)
                print check_price2, current_price2
            # 金价分析
            else:
                # 当前时间是内源还是外源
                source_type = 'inner' if get_source_type() else 'outer'
                # 然后得到获取的最新金价
                importance_dic = redis_cli.hgetall('gold_price_importance_{}'.format(source_type))
                number = importance_dic.get('priority') or '1'
                current_price_dic = redis_cli.hgetall('gold_price_source_{}'.format(number))

                # 内源不处理, 外源要按照比例转换成人民币价格
                current_price = current_price_dic.get('price')
                if source_type == 'outer':
                    check_price_standard = redis_cli.hgetall('python_gold_price_check')
                    inner_price = check_price_standard.get('inner_price') or get_close_price(redis_cli)[0]
                    outer_price = check_price_standard.get('outer_price') or get_close_price(redis_cli)[1]
                    current_price = Decimal(current_price) * Decimal(inner_price) / Decimal(outer_price)

                check_price = redis_cli.hget('python_gold_price', 'buy_check_price') or get_close_price(redis_cli)[0]
                # 获取需要更新进去的价格
                check_price2, current_price2 = get_real_price(redis_cli, current_price, check_price)

            # 更新实时金价
            # 确定金价后更新进redis
            check_price2 = Decimal(check_price2).quantize(Decimal('0.01'))
            current_price2 = Decimal(current_price2).quantize(Decimal('0.01'))
            set_current_price(redis_cli, check_price2, current_price2)

            time.sleep(1)

