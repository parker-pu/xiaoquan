#!/usr/share/app/anaconda3/bin/python3
# encoding: utf-8  

""" 
@version: v1.0 
@author: pu_yongjun
"""
from sqlalchemy import Column, String, Boolean, DateTime, Table, MetaData, text


class MeCreateTable(object):

    def __init__(self, engine):
        self.engine = engine
        self.metadata = MetaData(self.engine)

    def create_tables(self):
        """ 存放的是一些需要去执行的表结构，针对的是MySQL，其余数据库可能微调
        """
        didi_quan = Table(
            "didi_quan", self.metadata,

            Column('pk_md5', String(32), primary_key=True),
            Column('title', String(150)),
            Column('nums_rmb', String(100)),
            Column('nums_pro', String(100)),
            Column('context', String(100)),
            Column('city', String(100)),
            Column('img_url', String(200)),
            Column('orc_url', String(200)),
            Column('insert_time', DateTime, nullable=False,
                   server_default=text("CURRENT_TIMESTAMP")),
            Column('update_time', DateTime),
            Column('active', Boolean, server_default=text("'1'"), nullable=False)
        )

    def create_all(self):
        """ 创建所有的表
        （1）执行 create_tables 创建表的 metadata
        （2）执行 create_all 创建所有表
        """
        self.create_tables()
        self.metadata.create_all(self.engine)
