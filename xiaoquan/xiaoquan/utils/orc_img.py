#!/usr/share/app/anaconda3/bin/python3
# -*- coding: utf-8 -*-

""" 
@version: v1.0
@contact: pu_yongjun
"""
import os

from PIL import Image
import zbarlight


def ocr_qr_code(file_path):
    """ 这个函数的作用是用来返回二维码扫描的结果
    :param file_path:
    :return:
    """
    with open(file_path, 'rb') as f:
        image = Image.open(f)
        image.load()

    codes = None
    try:
        codes = zbarlight.scan_codes(['qrcode'], image)
    except Exception as e:
        print(e)
    finally:
        # 删除文件
        os.remove(file_path)
    return codes
