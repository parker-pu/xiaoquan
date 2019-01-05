#!/usr/bin/env python
# encoding: utf-8
"""
@author: pu yong_jun

数据库入库模块--只适合接入已有数据库，不创建和修改表结构
注意：所映射表中必须有主键
注意：SQLAlchemy本身没有提供修改表结构（schema）的方式，
可通过Alembic或SQLAlchemy-Migrate修改表结构
# 数据库常见异常
"""

import logging
import re
import time
from collections import Iterable
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

# 数据库操作类：PG
logger = logging.getLogger(__name__)


class RDBMSConn(object):
    """ 这个类是用来操作数据库的基类
    """

    def __init__(self, db_conn, schema_name, *conditions):
        """ 初始化数据库所需配置
        :param pg_conn: 数据库连接
        :param schema_name: 模式名
        :param conditions:
        """
        # 转换unicode编码 convert_unicode=True 打印详细SQL echo=True
        self.engine = create_engine(
            db_conn, convert_unicode=True,
            pool_size=100, pool_recycle=3600, echo=False
        )
        self.schema_name = schema_name
        self.sess = sessionmaker(bind=self.engine)
        self.class_dict = {}
        self.logger = logging.getLogger('DataBasePG')
        self.conditions = conditions if conditions else ('pk_md5',)  # where条件

    def process_dict(self, obj_dict, metric_pk='all', *conditions):
        """ 字典入库，样例：{表名: [{字段1: 值1, 字段2: 值2},]}
        :param obj_dict:
        :param metric_pk:
        :param conditions:
        :return:
        """
        if not isinstance(obj_dict, dict):
            return
        for key, values in obj_dict.items():
            if not isinstance(values, Iterable) or not values:
                continue
            self.__check_class(key)  # 检查表是否存在，如果不存在那就创建表
            if conditions:
                tup_pks = conditions
            elif self.conditions:
                tup_pks = self.conditions
            else:
                model = self.class_dict[key]
                primary_keys = [c.name for c in model.__table__.primary_key]  # 默认通过主键增删改
                primary_keys.reverse()  # 倒序
                tup_pks = tuple(primary_keys)
            self.process_base(key, values, metric_pk, *tup_pks)
        pass

    # 字典入库，重试五次
    def process_base(self, table_name, data_rows, metric_pk, *conditions):
        error_max = 5
        while error_max:
            try:
                self.__process_base(table_name, data_rows, metric_pk, *conditions)
                break
            except Exception as e:
                self.logger.error('{}:{}'.format(type(e), e))
                error_max -= 1
                time.sleep(1)
        pass

    # 字典入库
    def __process_base(self, table_name, data_rows, metric_pk, *conditions):
        start_time = time.clock()
        data_rows_insert, data_rows_update = self.batch_select(
            table_name, data_rows, *conditions
        )
        select_time, insert_time, update_time = time.clock() - start_time, 0, 0
        model = self.class_dict[table_name]
        if data_rows_insert:
            start_time_insert = time.clock()
            with self.session_scope() as session:
                session.bulk_insert_mappings(model, data_rows_insert)
            insert_time = time.clock() - start_time_insert
        if data_rows_update:
            start_time_update = time.clock()
            with self.session_scope() as session:
                session.bulk_update_mappings(model, data_rows_update)
            update_time = time.clock() - start_time_update

        # 执行操作表的操作
        if table_name in ['schedule']:
            self.execute("select beitai.update_game_task();")
        else:
            pass

        # 统计各个指标数据，把数据发送到
        all_time = time.clock() - start_time
        insert_data_num = len(data_rows_insert)
        update_data_num = len(data_rows_update)
        sum_data_num = len(data_rows_insert) + len(data_rows_update)
        log_text = (
            '\n+++++++++++++++ {0}.{1} +++++++++++++++'
            '\n=============== time =============='
            '\nselect:{2:.3f}'
            '\ninsert:{3:.3f}'
            '\nupdate:{4:.3f}'
            '\nsum:{5:.3f}'
            '\n=============== num =============='
            '\nsum:{6:d}'
            '\ninsert:{7:d}'
            '\nupdate:{8:d}'
            '\n++++++++++++++++++++++++++++++++++++++'
        )
        self.logger.info(log_text.format(
            self.schema_name, table_name, select_time, insert_time, update_time, all_time
            , sum_data_num, insert_data_num, update_data_num
        ))

        # # 统计指标入库 （influxDB）
        # send_dict = {
        #     'time.all': all_time, 'time.select': select_time, 'data.sum': sum_data_num,
        #     'data.insert': insert_data_num, 'time.insert': insert_time,
        #     'data.update': update_data_num, 'time.update': update_time,
        # }
        # self.stats.batch_send_value(batch_dict=send_dict, table_name=table_name, metric_pk=metric_pk)
        pass

    # 检测并创建匿名类
    def __check_class(self, name):
        if name not in self.class_dict.keys():
            # ArgumentError: Mapper Mapper could not assemble any primary key columns for mapped table
            table = Table(
                name,
                MetaData(schema=self.schema_name, bind=self.engine),
                autoload=True
            )
            self.class_dict[name] = self.quick_mapper(table)
        pass

    # 检查字段并创建类实例
    def __create_model(self, table_name, data_dict):
        missing_fields = []
        model = self.class_dict[table_name]()
        for k, v in data_dict.items():
            if hasattr(model, k):
                setattr(model, k, v)
            else:
                missing_fields.append(k)
        if missing_fields:
            self.logger.error('表{}缺少字段{}'.format(
                table_name, '、'.join(missing_fields))
            )
            self.logger.warning('表{}字段修正：{}'.format(
                table_name, '、'.join(missing_fields))
            )
            sql = 'ALTER TABLE '
            sql += '"{}"."{}" {};'.format(
                self.schema_name, table_name,
                ', '.join(
                    ['ADD COLUMN "{}" varchar(100)'.format(x) for x in missing_fields]
                ))
            self.execute(sql)  # 执行增加字段SQL
            table = Table(table_name, MetaData(
                schema=self.schema_name,
                bind=self.engine
            ), autoload=True)
            self.class_dict[table_name] = self.quick_mapper(table)  # 重新创建映射类
            model = self.__create_model(table_name, data_dict)  # 重新实例化
        return model
        pass

    # 实例列表或单实例入库，样例：[类实例1, 类实例2] 或 (类实例1, 类实例2) 或 类实例
    def process_obj(self, obj):
        if isinstance(obj, Iterable):
            for model in obj:
                self.process_obj(model)
        elif obj:
            # 单实例入库，样例：类实例
            with self.session_scope() as session:
                session.merge(obj)  # session.add(model)
        else:
            pass
        pass

    # 反映射函数
    @staticmethod
    def quick_mapper(table):
        class GenericMapper(declarative_base()):
            __table__ = table

        return GenericMapper

    # 事务会话
    @contextmanager
    def session_scope(self):
        """提供围绕一系列操作的事务范围"""
        session = self.sess()
        try:
            yield session
            session.commit()
        except IntegrityError as e:
            print(type(e), e)
        except Exception as e:
            session.rollback()
            self.logger.error('{}:{}'.format(type(e), e))
            raise e
        finally:
            session.close()

    # 执行SQL
    def execute(self, sql, **kwargs):
        """ 执行SQL语句
        :param sql:
        :param kwargs:
        :return:
        """
        raw_sql = text(sql)
        with self.session_scope() as session:
            temp = session.execute(raw_sql, kwargs)
            if re.match(
                    pattern=r'^SELECT[\s\S]+$',
                    string=str(raw_sql).strip(),
                    flags=re.I
            ):
                temp = temp.fetchall()
                return temp

    # 对比数据是否有新的字段，有的话更新数据表字段
    def check_table(self, table_name, keys):
        sql = "SELECT "
        sql += "m.attname FROM pg_attribute m WHERE m.attrelid = "
        sql += "(SELECT a.oid FROM pg_class a,pg_namespace b WHERE "
        sql += "a.relname='{}' AND b.nspname='{}' AND a.relnamespace=b.oid".format(
            table_name, self.schema_name)
        sql += ") AND m.attstattarget<0"
        columns = [row[0] for row in self.execute(sql)]
        missing_fields = list(set(keys) - set(columns))
        if missing_fields:
            self.logger.error('表{}缺少字段{}'.format(
                table_name, '、'.join(missing_fields))
            )
            self.logger.warning('表{}字段修正：{}'.format(
                table_name, '、'.join(missing_fields))
            )
            sql = 'ALTER TABLE '
            sql += '"{}"."{}" {};'.format(
                self.schema_name, table_name,
                ', '.join(['ADD COLUMN "{}" varchar(100)'.format(x) for x in missing_fields]))
            self.execute(sql)  # 执行增加字段SQL

    @staticmethod
    def __splice_sql(data_rows, *conditions):
        """ 生成拼接SQL参数，样例：[{字段1: 值1, 字段2: 值2},]，(条件1，条件2)
        :param data_rows: 数据
        :param conditions: 主键
        :return:
        """
        col_keys, arg_keys, arg_dict = list(), list(), dict()
        for i, data_row in enumerate(data_rows):
            for k, value in data_row.items():
                if conditions and k not in conditions:
                    continue
                if k not in col_keys:
                    col_keys.append(k)
                key = '{}_{}'.format(k, i)
                arg_dict[key] = value
            arg_keys.append(list())

        # 字段补遗
        for i, arg_key in enumerate(arg_keys):
            for k in col_keys:
                key = '{}_{}'.format(k, i)
                arg_key.append(key)
                if key not in arg_dict.keys():
                    arg_dict[key] = None
        return col_keys, arg_keys, arg_dict
        pass

    def batch_insert(self, table_name, data_rows):
        """ 批量插入，样例：表名，[{字段1: 值1, 字段2: 值2},]
        :param table_name: 表名
        :param data_rows: 数据
        :return:

        insert into tbl1 (id,info,crt_time) values
        (1,'test',now()), (2,'test2',now()), (3,'test3',now());

        """
        if not data_rows:
            return
        for data_row in data_rows:
            self.check_table(table_name, data_row.keys())
        table_name = '"{}"."{}"'.format(self.schema_name, table_name)
        col_keys, arg_keys, arg_dict = self.__splice_sql(data_rows)
        sql = 'INSERT INTO '
        sql += '{} ("{}") VALUES '.format(table_name, '", "'.join(col_keys))
        sql += ','.join(['(:{})'.format(
            ', :'.join([k for k in arg_key])) for arg_key in arg_keys]
        )
        sql += ';'
        self.execute(sql, **arg_dict)
        pass

    # 批量更新
    def batch_update(self, table_name, data_rows, *conditions):
        """ 批量更新
        :param table_name: 表名
        :param data_rows: 数据
        :param conditions:
        :return:

        update test set info=tmp.info from (values
        (1,'new1'),(2,'new2'),(6,'new6')) as tmp (id,info)
        where test.id=tmp.id;
        """
        table_name = '"{}"."{}"'.format(self.schema_name, table_name)
        col_keys, arg_keys, arg_dict = self.__splice_sql(data_rows)
        sql = 'UPDATE {} SET '.format(table_name)
        sql += ', '.join(['"{}"=tmp."{}"'.format(
            col_key, col_key) for col_key in col_keys]
        )
        sql += ' FROM (VALUES '
        sql += ','.join(['(:{})'.format(
            ', :'.join([k for k in arg_key])) for arg_key in arg_keys]
        )
        sql += ') AS tmp ("{}")'.format('", "'.join(col_keys))
        sql += ' WHERE {}'.format(' AND '.join(
            ['{}."{}"=tmp."{}"'.format(table_name, c, c) for c in conditions]
        ))
        sql += ';'
        # print(sql)
        self.execute(sql, **arg_dict)
        pass

    # 批量删除
    def batch_delete(self, table_name, data_rows, *conditions):
        # delete from test using (values (3),(4),(5)) as tmp(id) where test.id=tmp.id;
        table_name = '"{}"."{}"'.format(self.schema_name, table_name)
        col_keys, arg_keys, arg_dict = self.__splice_sql(data_rows, *conditions)
        sql = 'DELETE FROM '
        sql += '{} USING (VALUES '.format(table_name)
        sql += ','.join(['(:{})'.format(
            ', :'.join([k for k in arg_key])) for arg_key in arg_keys]
        )
        sql += ') AS tmp ("{}")'.format('", "'.join(col_keys))
        sql += ' WHERE {}'.format(' AND '.join(
            ['{}."{}"=tmp."{}"'.format(table_name, c, c) for c in conditions]
        ))
        sql += ';'
        print(sql)
        self.execute(sql, **arg_dict)
        pass

    def batch_select(self, table_name, data_rows, *conditions):
        """ 根据主键查询哪些数据需要插入，哪些需要更新
        :param table_name: 表名
        :param data_rows: 数据
        :param conditions: 主键
        :return:

        # 批量查询，用于批量更新/插入前的准备工作
        """
        table_name = '{}.{}'.format(self.schema_name, table_name)

        in_data_dict = dict(zip(
            conditions, [list(map(
                lambda x: '"{}"'.format(x.get(c)), data_rows)
            ) for c in conditions]
        ))
        sql = 'SELECT '
        sql += ', '.join(['{}'.format(c) for c in conditions])
        sql += ' FROM {}'.format(table_name)
        sql += ' WHERE {}'.format(' AND '.join(
            ['{} IN ({})'.format(k, ','.join(v))
             for k, v in in_data_dict.items()]
        ))
        sql += ';'
        res = self.execute(sql)
        data_rows_insert, data_rows_update = list(), list()
        for data_row in data_rows:
            pk_data = tuple(data_row.get(c) for c in conditions)
            if pk_data in res:
                data_rows_update.append(data_row)
            else:
                data_rows_insert.append(data_row)
        # print(res, data_rows_insert, data_rows_update)
        return data_rows_insert, data_rows_update
        pass
