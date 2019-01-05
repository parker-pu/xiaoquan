# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from db.rdb_base import RDBMSConn
from db.rdb_model import MeCreateTable
from xiaoquan.settings import DB_CONN


class MySQLPipeline(RDBMSConn):
    """ 这个管道
    """

    def __init__(self, db_conn, schema_name):
        super(MySQLPipeline, self).__init__(db_conn, schema_name)

    def open_spider(self, spider):
        """ 启动爬虫的时候需要做的事情

        创建数据库所需的表
        :param spider:
        :return:
        """
        ta = MeCreateTable(self.engine)
        ta.create_all()

    def lose_spider(self, spider):
        """ 关闭爬虫的时候需要做的事情
        :param spider:
        :return:
        """
        pass

    @classmethod
    def from_crawler(cls, spider):
        """ 初始化爬虫所需的一些操作
        :param spider:
        :return:
        """
        return cls(
            db_conn=DB_CONN.get("MySQL").get("db_conn"),
            schema_name=DB_CONN.get("MySQL").get("schema_name")
        )

    def process_item(self, item, spider):
        self.process_dict(
            {item.get('table_name'): item.get('data_rows')},
        )
        pass
