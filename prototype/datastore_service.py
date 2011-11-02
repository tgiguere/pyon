#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.core.exception import NotFound
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from interface.services.idatastore_service import BaseDatastoreService

class DataStoreService(BaseDatastoreService):

    def service_init(self):
        if self.CFG["type"] == 'CouchDB':
            self.datastore = CouchDB_DataStore()
            if 'force_clean' in self.CFG:
                if self.CFG['force_clean'] == True:
                    try:
                        self.datastore.delete_datastore()
                    except NotFound:
                        pass
                    self.datastore.create_datastore()
        else:
             self.datastore = MockDB_DataStore()

    def create_datastore(self, datastore_name=''):
        return self.datastore.create_datastore(datastore_name)

    def delete_datastore(self, datastore_name=''):
        return self.datastore.delete(object, datastore_name)

    def list_datastores(self):
        return self.datastore.list_datastores()

    def info_datastore(self, datastore_name=''):
        return self.datastore.info_datastore(datastore_name)

    def list_objects(self, datastore_name=''):
        return self.datastore.list_objects(datastore_name)

    def list_object_revisions(self, object_id='', datastore_name=''):
        return self.datastore.list_object_revisions(object_id, datastore_name)

    def create(self, object={}, datastore_name=''):
        return self.datastore.create(object, datastore_name)

    def create_doc(self, object={}, datastore_name=''):
        return self.datastore.create_doc(object, datastore_name)

    def read(self, object_id='', rev_id='', datastore_name=''):
        return self.datastore.read(object_id, rev_id, datastore_name)

    def read_doc(self, object_id='', rev_id='', datastore_name=''):
        return self.datastore.read_doc(object_id, rev_id, datastore_name)

    def update(self, object={}, datastore_name=''):
        return self.datastore.update(object, datastore_name)

    def update_doc(self, object={}, datastore_name=''):
        return self.datastore.update_doc(object, datastore_name)

    def delete(self, object={}, datastore_name=''):
        return self.datastore.delete_doc(object, datastore_name)

    def delete_doc(self, object={}, datastore_name=''):
        return self.datastore.delete_doc(object, datastore_name)

    def find(self, criteria=[], datastore_name=''):
        return self.datastore.find(criteria, datastore_name)

    def find_doc(self, criteria=[], datastore_name=''):
        return self.datastore.find_doc(criteria, datastore_name)

    def find_by_association(self, criteria=[], association="", datastore_name=""):
        return self.datastore.find_by_association(criteria, association, datastore_name)

    def find_by_association_doc(self, criteria=[], association="", datastore_name=""):
        return self.datastore.find_by_association_doc(criteria, association, datastore_name)

    def resolve_association(self, subject="", predicate="", object="", datastore_name=""):
        return self.datastore.resolve_association(tuple, datastore_name)

    def resolve_association_doc(self, subject="", predicate="", object="", datastore_name=""):
        return self.datastore.resolve_association_doc(tuple, datastore_name)
