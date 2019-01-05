#!/usr/share/app/anaconda3/bin/python3
# -*- coding: utf-8 -*-

""" 
@version: v1.0 
@author: pu_yongjun
"""
import hashlib
import re
import time


def gen_md5(str_con):
    """ 把输入的数据转换成MD5
    :param str_con: 输入的数据
    :return:
    """
    hl = hashlib.md5()
    hl.update(str(str_con).encode(encoding='utf-8'))
    return hl.hexdigest()


def get_today():
    """这个函数的作用是返回当前的时间"""
    today = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    return today


def get_index_arr(arr, index, default=None):
    """ 这个函数的作用是根据 index 获取数组中的元素
    :param arr: 数组
    :param index: 数组中的索引位置
    :param default: 默认填充值
    :return:
    """
    if index >= len(arr):
        return default
    else:
        text = arr[index]
        if text in [None, '']:
            return None
        else:
            return str(text).strip()


def re_didi_title(title):
    """ 这个函数是用来做滴滴优惠券标题切割

    主要切割为三部分
    （1）数字（元，打折）
    （2）标题
    （3）地区
    :param title: 标题
    :return:
    """
    if not title:
        return []

    try:
        nums_rmb = ','.join(re.findall("(\d*元)", title))  # 优惠元
        nums_pro = ','.join(re.findall("(\d+\.*\d*折)", title))  # 打折

        if "（" in title:
            re_title = str(title).split("（")
            context = get_index_arr(re_title, 0)
            city = str(get_index_arr(re_title, 1, '')).replace("）", "")
        elif "(" in title:
            re_title = str(title).split("(")
            context = get_index_arr(re_title, 0)
            city = str(get_index_arr(re_title, 1, '')).replace(")", "")
        elif "【" in title:
            re_title = str(title).split("【")
            context = get_index_arr(re_title, 0)
            city = str(get_index_arr(re_title, 1, '')).replace("】", "")
        else:
            context = None
            city = None

        return replace_none([nums_rmb, nums_pro, context, city])

    except Exception as e:
        print(e)
        return []


def replace_none(arr, default=None):
    """ 这个函数的作用是替换调数组中的空值与空串
    :param arr: 需要替换的数组
    :param default: 默认的替换值
    :return:
    """
    return list(map(lambda x: default if x in [None, ''] else x, arr))
