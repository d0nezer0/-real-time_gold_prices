# -*- coding: utf-8 -*-
import time
import datetime
from decimal import Decimal

import requests
import sys

import MySQLdb as mydb


db_config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'd0ne',
    'passwd': 'd0ne',
    'db': 'gold',
    'charset': 'utf8'
}


def get_response(url, headers=None):
    """
    :param url:
    :param headers: dict or None
    :return:
    """
    try:
        response = requests.get(url, headers=headers)
        text = response.text
        return {'status_code': response.status_code, 'text': text}
    except Exception, e:
        # todo 报警
        print >> sys.stderr, u'redis connection error with {}'.format(e.message)
        return {'status_code': 400, 'text': e.message}


def get_source_type():
    """
    国内源的时间是  上午9:00--11:30   下午13;30--15:30    晚上20:00-2:30
    :return:    国内为 True
    """
    now = datetime.datetime.now()
    if 9 <= now.hour <= 11 or (11 == now.hour and now.minute <= 30):
        return True
    elif (13 == now.hour and now.minute >= 30) or (14 <= now.hour <= 15) or (15 == now.hour and now.minute <= 30):
        return True
    elif 20 <= now.hour or (0 <= now.hour <= 2) or (2 == now.hour and now.minute <= 30):
        return True
    else:
        return False


def get_real_price(redis_cli, current_price, check_price=0, adjust=False):
    """
    premium = models.DecimalField(u'溢价(元/克)', max_digits=5, decimal_places=2, default=0)
    min_check = models.DecimalField(u'最小波动(元/克)', max_digits=5, decimal_places=2, default=0)
    max_wave_percent = models.DecimalField(u'最大波动率', choices=MAX_WAVE_PERCENT_CHOICE,
                                           max_digits=5, decimal_places=3, default=Decimal('0.10'))
    step_type = models.CharField(u'步类型', max_length=20, choices=STEP_TYPE_CHOICE, null=False, default='')
    small_step = models.DecimalField(u'小步', choices=SMALL_STEP_CHOICE,
                                     max_digits=5, decimal_places=4, default=Decimal('0.10'))
    big_step = models.DecimalField(u'大步', choices=BIG_STEP_CHOICE,
                                   max_digits=5, decimal_places=4, default=Decimal('0.10'))
    max_alarm = models.SmallIntegerField(u'最大连续报警次数', blank=False, null=False)
    update_time = models.SmallIntegerField(u'权重值更新时间', blank=False, null=False, default=60,
                                           help_text=u'单位是秒，默认60S')
    :param redis_cli:
    :param check_price:     上一次的 check_price
    :param current_price:   这次权重最高的价格
    :return:    返回处理后的当前价格和上一次变化价格
    """
    current_price = Decimal(current_price)
    check_price = Decimal(check_price)

    if not check_price:
        check_price = current_price

    args_dic = redis_cli.hgetall('gold_price_adjust')

    premium = Decimal(args_dic.get('premium'))
    min_wave = args_dic.get('min_check')
    max_wave_percent = args_dic.get('max_wave_percent')
    step_type = args_dic.get('step_type')
    small_step = args_dic.get('small_step')
    big_step = args_dic.get('big_step')
    # premium = args_dic.get('')

    wave_price = abs(check_price - current_price)

    # 普通调价的时候
    if adjust:
        if check_price - current_price < 0:
            premium = -premium
        return current_price, current_price + Decimal(premium)

    # 正常价格
    # 情况1 ：波动值 小于等于 最小波动
    # 显示 ： 上一秒默认显示的金价，不更新。
    if wave_price < Decimal(min_wave):
        return check_price, check_price
    else:
        step = small_step if step_type == 'small' else big_step
        step = Decimal(step)
        wave_percent = wave_price / check_price

        # 情况2：波动值 大于 最小波动 并且 波动率 小于等于 当前设置的步
        # 显示 ：  这一秒抓取的金价+溢价.
        if wave_percent <= step:
            return check_price, current_price + premium
        # 情况3： 波动率 大于 当前设置的步 小于 最大波动
        # 显示 ：  前一秒的默认显示金价 + -前一秒的显示金价（基值） * 步。
        elif step < wave_percent < max_wave_percent:
            return check_price, check_price + check_price * step
        # 情况4： 波动率 大于 最大波动
        # 显示 ：  上一秒默认显示的金价， 不更新，并报警。
        else:
            # TODO alert
            return check_price, check_price


def set_expire_time(redis_cli, key, value):
    struct_time = time.localtime(key)

    day_key = 'day_{}'.format(key)
    week_key = 'week_{}'.format(key)
    month_key = 'month_{}'.format(key)

    # 过期时间为 key 之后的 1 天, 当前时间不影响
    # day_expire_time = 24 * 60 * 60 + int(key) - int(time.time())
    # day_expire_time = 1 if day_expire_time < 0 else day_expire_time
    # 改成存储当天的信息
    gm = time.localtime()
    time_struct = time.struct_time((gm.tm_year, gm.tm_mon, gm.tm_mday + 1, 0, 0, 0, 0, 0, 0))
    tomorrow = time.mktime(time_struct)

    # day_expire_time = tomorrow - key + 1   # +1 避免边界0点取不到.
    # # 现在这里是处理如果没有数据, 现跑的时候, 过期时间应该与当前时间相关.
    # passed_time = time.time() - key
    # day_expire_time -= passed_time

    # 等同于 明天凌晨 - 当前时间.
    day_expire_time = tomorrow - int(time.time()) + 1

    if day_expire_time > 24 * 60 * 60 + 5 or tomorrow - key > 24 * 60 * 60 + 5:
        day_expire_time = 1

    # 过期时间为 key 之后的 7 天, 当前时间不影响
    week_expire_time = 7 * 24 * 60 * 60 + int(key) - int(time.time())
    week_expire_time = 1 if week_expire_time < 0 else week_expire_time
    # 过期时间为 key 之后的 30 天, 当前时间不影响
    month_expire_time = 30 * 24 * 60 * 60 + int(key) - int(time.time())
    month_expire_time = 1 if month_expire_time < 0 else month_expire_time

    # 分别检查 天, 周, 月 是否有数据, 没有就加上.
    if struct_time.tm_min % 10 == 0 and not redis_cli.exists(day_key):
        redis_cli.set(day_key, value, int(day_expire_time))
        # 整时的话 同时保存到数据库 (秒)
        if struct_time.tm_min == 0 and struct_time.tm_sec and not redis_cli.exists(week_key):
            redis_cli.set(week_key, value, int(week_expire_time))
            save_gold_price(value, key)
        if struct_time.tm_min == 0 and struct_time.tm_sec and struct_time.tm_hour % 4 == 2 \
                and not redis_cli.exists(month_key):
            redis_cli.set(month_key, value, int(month_expire_time))


def save_gold_price(price, time_stamp):
    """
    保存每个小时的价格,
    :param price:
    :param time_stamp:
    :return:
    """
    struct_time = time.localtime(time_stamp)
    create_time = datetime.datetime(struct_time.tm_year, struct_time.tm_mon, struct_time.tm_mday, struct_time.tm_hour)
    try:
        conn = mydb.connect(**db_config)
        conn.autocommit(1)
        cursor = conn.cursor()
        sql = 'INSERT INTO goldbox_goldtrade_goldpricehistory (price, create_time) values("{}", "{}")'.format(Decimal(price), create_time)
        cursor.execute(sql)
        conn.close()
    except Exception, e:
        print >> sys.stderr, 'save_gold_price failed with {}'.format(e.message)


def set_current_price(redis_cli, check_price, current_price):
    """
    每秒设置价格
    :param redis_cli:
    :param check_price:
    :param current_price:
    :return:
    """
    current_time = int(time.time())
    redis_cli.hset('python_gold_price', 'buy_price', current_price)
    redis_cli.hset('python_gold_price', 'sell_price', current_price)
    redis_cli.hset('python_gold_price', 'buy_check_price', check_price)
    redis_cli.hset('python_gold_price', 'sell_check_price', check_price)
    redis_cli.hset('python_gold_price', 'current_time', current_time)
    # 开盘价和计息价(中午两点)
    date_time = datetime.datetime.fromtimestamp(current_time)
    if date_time.hour == 9 and date_time.minute == 0 and date_time.second == 0:
        redis_cli.hset('python_gold_price', 'first_price', current_price)
    if date_time.hour == 14 and date_time.minute == 0 and date_time.second == 0:
        redis_cli.hset('python_gold_price', 'standard_price', current_price)

    # 每十分钟的, 存成天数据
    # 每小时的, 存成周数据
    # 每四小时, 存成月数据
    if date_time.second == 0 and date_time.minute % 10 == 0:
        set_expire_time(redis_cli, current_time, current_price)

    # if date_time.second == 0 and date_time.minute == 0:
    #     save_gold_price(current_price, current_time)

    # 每天闭盘的时候, 存上最后一个价格进行比例转换
    # 上午9:00--11:30   下午13;30--15:30    晚上20:00-2:30
    if (date_time.hour == 11 and date_time.minute == 30 and date_time.second == 0) or (
                        date_time.hour == 15 and date_time.minute == 30 and date_time.second == 0) or (
                        date_time.hour == 2 and date_time.minute == 30 and date_time.second == 0):

        inner_num = redis_cli.hget('gold_price_importance_inner', 'priority')
        outer_num = redis_cli.hget('gold_price_importance_outer', 'priority')

        inner_price = redis_cli.hget('gold_price_source_{}'.format(inner_num), 'price')
        outer_price = redis_cli.hget('gold_price_source_{}'.format(outer_num), 'price')
        redis_cli.hset('python_gold_price_check', 'inner_price', inner_price)
        redis_cli.hset('python_gold_price_check', 'outer_price', outer_price)


def get_close_price(redis_cli):
    """
    初始化的时候, 没有闭盘内外源价格, 获取最后标准价或者平均值
    :param redis_cli:
    :return:
    """
    inner_num = redis_cli.hget('gold_price_importance_inner', 'priority')
    outer_num = redis_cli.hget('gold_price_importance_outer', 'priority')
    inner_price = redis_cli.hget('gold_price_source_{}'.format(inner_num), 'price') or '0'
    outer_price = redis_cli.hget('gold_price_source_{}'.format(outer_num), 'price') or '0'
    return inner_price, outer_price

