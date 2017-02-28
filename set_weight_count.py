#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import decimal
import requests

from daemon import Daemon
import price_source
from get_source_gold_price import cust_popen, pidfile, stdin, stdout, stderr


currpath = os.path.join(os.getcwd(), os.path.dirname(__file__))
if currpath not in sys.path:
    sys.path.append(currpath)


def check_server_start():
    check_start = 'ps aux |grep set_weight_count.py'
    retcode, proc = cust_popen(check_start)
    result = proc.stdout.readlines()
    if len(result) > 3:
        return False
    else:
        return True


def get_variance(datas):
    """
    比较一组数的方差, 返回最大
    :param datas:   [('gold_source_price_1', '275.59'), ('gold_source_price_2', '229'), ('gold_source_price_3', '230')]
    :return:
    """
    variance_dic = dict()
    count = len(datas)

    # 这组数据对应的金价列表       [Decimal('100'), Decimal('200'), Decimal('250')]
    numbers = [decimal.Decimal(v[1]) for v in datas]

    for i in range(count):
        variance_sum = 0
        for num in numbers:
            variance_sum += (numbers[i] - num) ** 2
        variance = (variance_sum / decimal.Decimal(count - 1)) ** decimal.Decimal(0.5)
        print variance_sum, variance

        variance_dic.setdefault(datas[i][0], variance)

    return sorted(variance_dic.items(), key=lambda d: d[1], reverse=True)


class WeightServer(Daemon):
    """
    这个daemon 只用来定时计算和更新权重
    """
    def run(self):
        redis_cli = price_source.get_redis_cli()

        while True:
            sleep_count = redis_cli.get('sleep_count', 60)

            # call count method
            keys = map(lambda i: 'gold_source_price_{}'.format(i), range(1, 12))
            values = redis_cli.mget(keys)

            datas = zip(keys, values)

            # 内源有数据 6个
            if sum(values[:6]):
                check_datas = datas[:6]
            # 使用境外源
            else:
                check_datas = datas[6:]

            # [('gold_source_price_1', '275.59'), ('gold_source_price_2', '229'), ('gold_source_price_3', '230')]
            useful_datas = [data for data in check_datas if data[1]]

            variances = get_variance(useful_datas)

            # ('gold_source_price_1', Decimal('127.4754878398196207507056027')
            # 第一个是方差最大的
            source_num, price = variances[0]

            # TODO
            # 自己判断是否要去更新
            requests.post()

            time.sleep(sleep_count)


def main():

    is_stop = check_server_start()
    daemon = WeightServer(pidfile, currpath, stdin, stdout, stderr)

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            if is_stop:
                print 'going start!'
                daemon.start()
            else:
                print 'python %s is already start' % sys.argv[0]
        elif 'stop' == sys.argv[1]:
            print 'going stop!'
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            print 'going restart!'
            daemon.restart()
        # elif 'test' == sys.argv[1]:
        #     test()
        else:
            print 'Unknown command'
            print "Usage: python %s start|stop|restart" % sys.argv[0]
            print "Example: python %s start" % sys.argv[0]
            sys.exit(2)
        sys.exit(0)

    else:
        print "Usage: python %s start|stop|restart" % sys.argv[0]
        print "Example: python %s start" % sys.argv[0]
        sys.exit(2)


if __name__ == '__main__':
    main()

