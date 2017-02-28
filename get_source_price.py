#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import threading

import sys

import subprocess
import traceback

from daemon import Daemon
import price_source

currpath = os.path.join(os.getcwd(), os.path.dirname(__file__))
if currpath not in sys.path:
    sys.path.append(currpath)
pidfile = os.path.join(currpath, 'tmp/main.pid')
stdin = '/dev/null'
stdout = os.path.join('/var/log/goldbox/gold_price/', 'stdout.log')
stderr = os.path.join('/var/log/goldbox/gold_price/', 'stderr.log')


class ExecCommandError(Exception):
    pass


def cust_popen(cmd, close_fds=True):
    try:
        proc = subprocess.Popen('sudo %s' % cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=close_fds)
        retcode = proc.wait()
        return retcode, proc
    except Exception, e:
        print >> sys.stderr, traceback.print_exc()
        raise ExecCommandError, e


def check_server_start():
    check_start = 'ps aux |grep get_source_gold_price.py'
    retcode, proc = cust_popen(check_start)
    result = proc.stdout.readlines()
    if len(result) > 3:
        return False
    else:
        return True


class SystemServer(Daemon):

    def run(self):

        lock1 = threading.RLock()
        lock2 = threading.RLock()
        lock3 = threading.RLock()
        lock4 = threading.RLock()
        lock5 = threading.RLock()
        lock6 = threading.RLock()
        lock7 = threading.RLock()
        lock8 = threading.RLock()
        lock9 = threading.RLock()
        lock10 = threading.RLock()
        lock11 = threading.RLock()
        lock12 = threading.RLock()

        s1 = price_source.SourcePrice('111', lock1, 1)
        s2 = price_source.SourcePrice('222', lock2, 2)
        s3 = price_source.SourcePrice('333', lock3, 3)
        s4 = price_source.SourcePrice('444', lock4, 4)
        s5 = price_source.SourcePrice('555', lock5, 5)
        s6 = price_source.SourcePrice('666', lock6, 6)

        s7 = price_source.SourcePrice('777（外）', lock7, 7)
        s8 = price_source.SourcePrice('888（外）', lock8, 8)
        s9 = price_source.SourcePrice('999（外）', lock9, 9)
        s10 = price_source.SourcePrice('000（外）', lock10, 10)
        s11 = price_source.SourcePrice('989（外）', lock11, 11)
        s12 = price_source.RealPrice('999（外）', lock12, 12)

        s1.start()
        s2.start()
        s3.start()
        s4.start()
        s5.start()
        s6.start()
        s7.start()
        s8.start()
        s9.start()
        s10.start()
        s11.start()
        s12.start()

        s1.join()
        s2.join()
        s3.join()
        s4.join()
        s5.join()
        s6.join()
        s7.join()
        s8.join()
        s9.join()
        s10.join()
        s11.join()
        s12.join()


def test():
    # i = 0
    # while 1:
    #     f = open(stdout, 'a+')
    #     i += 1
    #     print >> f, '{}'.format(i)
    #     f.close()
    #     time.sleep(1)
    lock = threading.RLock()

    s1 = price_source.SourcePrice('111', lock, 1)
    s2 = price_source.SourcePrice('222', lock, 2)
    s3 = price_source.SourcePrice('333', lock, 3)
    s4 = price_source.SourcePrice('444', lock, 4)
    s5 = price_source.SourcePrice('555', lock, 5)
    s6 = price_source.SourcePrice('666', lock, 6)

    s7 = price_source.SourcePrice('777（外）', lock, 7)
    s8 = price_source.SourcePrice('888（外）', lock, 8)
    s9 = price_source.SourcePrice('999（外）', lock, 9)
    s10 = price_source.SourcePrice('000（外）', lock, 10)
    s11 = price_source.SourcePrice('989（外）', lock, 11)
    s12 = price_source.RealPrice('999（外）', lock, 12)

    s1.start()
    s2.start()
    s3.start()
    s4.start()
    s5.start()
    s6.start()
    s7.start()
    s8.start()
    s9.start()
    s10.start()
    s11.start()
    s12.start()

    s1.join()
    s2.join()
    s3.join()
    s4.join()
    s5.join()
    s6.join()
    s7.join()
    s8.join()
    s9.join()
    s10.join()
    s11.join()
    s12.join()


def main():

    is_stop = check_server_start()
    daemon = SystemServer(pidfile, currpath, stdin, stdout, stderr)

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
        elif 'test' == sys.argv[1]:
            test()
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

