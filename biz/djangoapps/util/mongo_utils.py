"""
MongoDB operation for Biz.
Add mongodb operation method by the need.
"""
from collections import OrderedDict
import copy
from datetime import datetime
import logging
import pytz
from mongodb_proxy import autoretry_read
from pymongo import ASCENDING

from biz.djangoapps.util.biz_mongo_connection import BizMongoConnection

log = logging.getLogger(__name__)

DEFAULT_DATETIME = datetime(9999, 1, 1, 0, 0, 0, 0, tzinfo=pytz.utc)


class BizStore(object):
    """
    Class for a MongoDB operation
    """

    def __init__(self, store_config, key_conditions=None, key_index_columns=None):
        """
        Referring to the MongoDB Connection of BizMongoConnection.
        Create a collection for MongoDB.

        :param store_config: setting of mongodb
        :param key_conditions: dict of conditions
        :param key_index_columns: list of index column
        :return:
        """
        try:
            self._db_connection = BizMongoConnection(**store_config)
            self._db = self._db_connection.database
            self._collection = self._db[store_config['collection']]
        except Exception as e:
            log.error("Error occurred while connecting MongoDB: %s" % e)
            raise
        self._key_conditions = key_conditions or {}
        self._key_index_columns = key_index_columns or []

    @autoretry_read()
    def get_document(self, conditions=None, excludes=None):
        """
        Get the data of MongoDB

        :param conditions: MongoDB Condition for Dict
        :param excludes: _id flag of exclusion
        :return: Conversion of pymongo.cursor.Cursor type to list
        """
        if conditions is None:
            conditions = {}
        _conditions = copy.deepcopy(self._key_conditions)
        _conditions.update(conditions)
        if excludes is None:
            excludes = ['_id']
        _excludes = dict((exclude, False) for exclude in excludes)
        try:
            return self._collection.find_one(_conditions, _excludes, as_class=OrderedDict)
        except Exception as e:
            log.error("Error occurred while find MongoDB: %s" % e)
            raise

    @autoretry_read()
    def get_documents(self, conditions=None, excludes=None, sort_column='_id', sort=ASCENDING, offset=0, limit=0):
        """
        Get the data of MongoDB

        :param conditions: MongoDB Condition for Dict
        :param excludes: _id flag of exclusion
        :param sort_column: Keys to sort
        :param sort: Sorting method
        :param offset: Offset to documents
        :param limit: Limit to documents (A limit() value of 0 (i.e. .limit(0)) is equivalent to setting no limit.)
        :return: Conversion of pymongo.cursor.Cursor type to list
        """
        if conditions is None:
            conditions = {}
        _conditions = copy.deepcopy(self._key_conditions)
        _conditions.update(conditions)
        if excludes is None:
            excludes = ['_id']
        _excludes = dict((exclude, False) for exclude in excludes)
        try:
            return list(
                self._collection.find(_conditions, _excludes, as_class=OrderedDict).skip(offset).limit(limit).sort(sort_column, sort)
            )
        except Exception as e:
            log.error("Error occurred while find MongoDB: %s" % e)
            raise

    @autoretry_read()
    def get_count(self, conditions=None):
        """
        Get the count of list

        :param conditions: MongoDB Condition for Dict
        :return: int
        """
        if conditions is None:
            conditions = {}
        _conditions = copy.deepcopy(self._key_conditions)
        _conditions.update(conditions)
        try:
            return self._collection.find(_conditions).count(True)
        except Exception as e:
            log.error("Error occurred while get count MongoDB: %s" % e)
            raise

    @autoretry_read()
    def aggregate(self, key_field_name, value_field_name, conditions=None):
        """
        Aggregate the amount by grouping the specified key

        :param key_field_name: field name for grouping
        :param value_field_name: field name for aggregation
        :param conditions: dict for conditions
        :return: dict
            e.g.)
            {
                u'key1': 100.0,
                u'key2': 200.0,
                u'key3': 300.0,
            }
        """
        if conditions is None:
            conditions = {}
        _conditions = copy.deepcopy(self._key_conditions)
        _conditions.update(conditions)
        try:
            result = self._collection.aggregate([
                {'$match': _conditions},
                {'$group': {'_id': '${}'.format(key_field_name), 'total': {'$sum': '${}'.format(value_field_name)}}},
            ])['result']
            return dict([(d['_id'], d['total']) for d in result])
        except Exception as e:
            log.error("Error occurred while processing aggregate to MongoDB: %s" % e)
            raise

    @autoretry_read()
    def set_documents(self, posts):
        """
        Data insert into MongoDB

        :param posts: dict data for inserting
        :return: _id
        """
        try:
            return self._collection.insert(posts, check_keys=False)
        except Exception as e:
            log.error("Error occurred while insert MongoDB: %s" % e)
            raise

    @autoretry_read()
    def ensure_indexes(self, index_columns=None):
        """
        Add Index

        :param index_columns: list type ex)index_columns['column1', 'column2']
        :return:
        """
        if index_columns is None:
            index_columns = []
        _index_columns = copy.deepcopy(self._key_index_columns)
        _index_columns.extend(index_columns)
        try:
            return [self._collection.create_index([(i, ASCENDING)]) for i in _index_columns]
        except Exception as e:
            log.error("Error occurred while ensure indexes MongoDB: %s" % e)
            raise

    @autoretry_read()
    def drop_indexes(self):
        """
        Drop Index

        :return:
        """
        self._collection.drop_indexes()

    @autoretry_read()
    def remove_documents(self, conditions=None):
        """
        Remove Documents

        :param conditions: MongoDB Condition for Dict
        :return: None
        """
        if conditions is None:
            conditions = {}
        _conditions = copy.deepcopy(self._key_conditions)
        _conditions.update(conditions)
        try:
            return self._collection.remove(_conditions)
        except Exception as e:
            log.error("Error occurred while remove documents MongoDB: %s" % e)
            raise
