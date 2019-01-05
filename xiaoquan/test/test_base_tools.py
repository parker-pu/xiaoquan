#!/usr/share/app/anaconda3/bin/python3
# encoding: utf-8  

""" 
@version: v1.0 
@author: pu_yongjun
"""
import unittest

from xiaoquan.utils.base_tools import re_didi_title


class TestTools(unittest.TestCase):
    """ 这是一个测试类
    """

    def test_re_didi_title(self):
        """ 测试切割滴滴优惠券信息
        """
        context1 = "滴滴出行送18元快车券（限上海用）"
        self.assertEqual(
            re_didi_title(context1),
            ['18元', None, '滴滴出行送18元快车券', '限上海用']
        )

        context2 = "滴滴出行送7.8折滴滴快车券（限温州使用）"
        self.assertEqual(
            re_didi_title(context2),
            [None, '7.8折', '滴滴出行送7.8折滴滴快车券', '限温州使用']
        )

        context3 = "滴滴出行送5元+9折滴滴快车券（限武汉使用）"
        self.assertEqual(
            re_didi_title(context3),
            ['5元', '9折', '滴滴出行送5元+9折滴滴快车券', '限武汉使用']
        )

        context4 = "滴滴出行派送30元快车红包【限四川除成都使用】"
        self.assertEqual(
            re_didi_title(context4),
            ['30元', None, '滴滴出行派送30元快车红包', '限四川除成都使用']
        )

        context5 = "滴滴出行送8.8折滴滴快车折扣券【限东三省使用】"
        self.assertEqual(
            re_didi_title(context5),
            [None, '8.8折', '滴滴出行送8.8折滴滴快车折扣券', '限东三省使用']
        )


if __name__ == '__main__':
    unittest.main()  # 运行所有的测试用例
