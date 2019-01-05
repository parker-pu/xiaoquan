# -*- coding: utf-8 -*-
import os
import scrapy
from xiaoquan.items import XQItem
from xiaoquan.settings import BASE_DIR
from xiaoquan.utils.base_tools import (
    gen_md5,
    get_today,
    get_index_arr,
    re_didi_title)
from xiaoquan.utils.orc_img import ocr_qr_code


class MokaDidiSpider(scrapy.Spider):
    name = 'moka_didi'
    start_urls = ['https://mp.weixin.qq.com/mp/homepage?__biz=MzI4NzM4MTQyMg==&hid=5']

    def parse(self, response):
        """ 这个是第一次解析的函数
        :param response:
        :return:
        """
        for line_url in response.xpath(
                "*//a[@class='list_item js_post']/@href"
        ).extract():
            yield scrapy.Request(
                url=line_url,  # 下一节需要的URL
                dont_filter=False,  # 是否需要过滤
                callback=self.context_page,  # 回调函数
            )

    def context_page(self, response):
        """ 这个方法是用来获取网页中的二维码图片
        :param response:
        :return:
        """
        data = dict(zip(
            response.xpath('*//blockquote')[::2],  # 偶数，也就是标题
            response.xpath('*//blockquote')[1::2]  # 奇数，也就是二维码

        ))
        for t, i in data.items():
            title = ''.join(t.xpath(
                'text()|'
                'span/text()|'
                '*//span/text()'
            ).extract())

            img_url = ''.join(i.xpath(
                'p/img/@data-src|'
                'img/@data-src|'
                '*//img/@data-src'
            ).extract())

            yield scrapy.Request(
                url=img_url,
                dont_filter=False,
                callback=self.context_result,
                meta={'title': title},
            )

    @staticmethod
    def context_result(response):
        """ 识别二维码内容，同时保存二维码数据
        :param response:
        :return:
        """
        item_context = dict()

        re_title_context = re_didi_title(response.meta.get('title'))
        item_context['title'] = response.meta.get('title')
        item_context['nums_rmb'] = get_index_arr(re_title_context, 0)
        item_context['nums_pro'] = get_index_arr(re_title_context, 1)
        item_context['context'] = get_index_arr(re_title_context, 2)
        item_context['city'] = get_index_arr(re_title_context, 3)

        item_context['img_url'] = response.url
        item_context['pk_md5'] = gen_md5(response.url)
        item_context['update_time'] = get_today()

        file_path = os.path.join(
            BASE_DIR,
            'img/{}.png'.format(gen_md5(response.url))
        )

        # 写图片
        with open(file_path, 'wb') as f:
            f.write(response.body)

        # 获取图片的URL
        item_context['orc_url'] = ocr_qr_code(file_path)

        # 返回数据给 Pipline
        back_item = XQItem()
        back_item['table_name'] = "didi_quan"
        back_item['data_rows'] = [item_context]
        yield back_item
