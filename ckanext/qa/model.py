import uuid
import datetime

from sqlalchemy import Column
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import ProgrammingError

import ckan.model as model
from ckan.lib import dictization
from ckan.plugins import toolkit

log = __import__('logging').getLogger(__name__)

Base = declarative_base()


def make_uuid():
    return unicode(uuid.uuid4())


class QAMigrations(Base):

    __tablename__ = 'qa_migrations'

    id = Column(types.UnicodeText, primary_key=True, default=make_uuid)
    created = Column(types.DateTime, default=datetime.datetime.now)

    @classmethod
    def count(cls):
        return model.Session.query(cls).count()


class QA(Base):
    """
    Contains the latest results per dataset/resource for QA tasks
    run against them.
    """
    __tablename__ = 'qa'

    id = Column(types.UnicodeText, primary_key=True, default=make_uuid)
    package_id = Column(types.UnicodeText, nullable=False, index=True)
    resource_id = Column(types.UnicodeText, nullable=False, index=True)
    resource_timestamp = Column(types.DateTime)  # key to resource_revision
    archival_timestamp = Column(types.DateTime)

    openness_score = Column(types.Integer)
    openness_score_reason = Column(types.UnicodeText)
    openness_score_reason_args = Column(types.UnicodeText)
    format = Column(types.UnicodeText)

    created = Column(types.DateTime, default=datetime.datetime.now)
    updated = Column(types.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        summary = 'score=%s format=%s' % (self.openness_score, self.format)
        details = unicode(self.openness_score_reason).encode('unicode_escape')
        package = model.Package.get(self.package_id)
        package_name = package.name if package else '?%s?' % self.package_id
        return '<QA %s /dataset/%s/resource/%s %s>' % \
            (summary, package_name, self.resource_id, details)

    def as_dict(self):
        context = {'model': model}
        qa_dict = dictization.table_dictize(self, context)
        return qa_dict

    @classmethod
    def get_for_resource(cls, resource_id):
        return model.Session.query(cls) \
                    .filter(cls.resource_id == resource_id) \
                    .first()

    @classmethod
    def get_for_package(cls, package_id):
        '''Returns the QA for the given package. May not be any if the package
        has no resources or has not been archived. It checks the resources are
        not deleted.'''
        return model.Session.query(cls) \
            .filter(cls.package_id == package_id) \
            .join(model.Resource, cls.resource_id == model.Resource.id) \
            .filter(model.Resource.state == 'active') \
            .all()

    @classmethod
    def create(cls, resource_id):
        c = cls()
        c.resource_id = resource_id

        # Find the package_id for the resource.
        q = model.Session.query(model.Package.id)
        if toolkit.check_ckan_version(max_version='2.2.99'):
            q = q.join(model.ResourceGroup)
        q = q.join(model.Resource) \
             .filter_by(id=c.resource_id)
        result = q.first()
        if not result or not result[0]:
            raise Exception("Missing dataset")
        c.package_id = result[0]
        return c


def aggregate_qa_for_a_dataset(qa_objs):
    '''Returns aggregated archival info for a dataset, given the archivals for
    its resources (returned by get_for_package).

    :param qa_objs: A list of the QA objects for a dataset's resources
    :type qa_objs: A list of QA objects
    :returns: QA dict about the dataset, with keys:
                openness_score
                openness_score_reason
                updated
    '''
    qa_dict = {'openness_score': None, 'openness_score_reason': None,
               'updated': None}
    for qa in qa_objs:
        # openness_score takes the highest i.e. optimistic
        # openness_score_reason matches the status_id
        if qa_dict['openness_score'] is None or \
                qa.openness_score > qa_dict['openness_score']:
            qa_dict['openness_score'] = qa.openness_score
            qa_dict['openness_score_reason'] = qa.openness_score_reason
            qa_dict['openness_score_reason_args'] = qa.openness_score_reason_args
        # updated is the newest of all the resources
        if qa_dict['updated'] is None or \
                qa.updated > qa_dict['updated']:
            qa_dict['updated'] = qa.updated
    if qa_dict['updated']:
        qa_dict['updated'] = qa_dict['updated'].isoformat()
    return qa_dict


def init_tables(engine):
    Base.metadata.create_all(engine)
    log.info('QA database tables are set-up')

    migration_number = QAMigrations.count()
    log.info('Migration number: %s', migration_number)
    migration_sql_list = [
        "ALTER TABLE qa ADD COLUMN openness_score_reason_args TEXT;"
    ]
    for counter, sql in enumerate(migration_sql_list, start=1):
        if migration_number < counter:
            try:
                log.debug(sql)
                model.Session.execute(sql)
            except ProgrammingError as e:
                print(e)
                log.debug('Migration have been rolled back.')
                model.Session.rollback()
            finally:
                model.Session.add(QAMigrations())
                model.Session.commit()

    model.Session.close()
