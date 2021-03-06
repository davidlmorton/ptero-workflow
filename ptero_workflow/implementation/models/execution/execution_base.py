from ..base import Base
from ..json_type import JSON, MutableJSONDict
from ptero_workflow.urls import url_for
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, String
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import backref, relationship
from ptero_workflow.implementation.exceptions import (OutputsAlreadySet,
        ImmutableUpdateError, InvalidStatusError)
from operator import attrgetter
from ptero_common import nicer_logging
from ptero_common import statuses

LOG = nicer_logging.getLogger(__name__)

__all__ = ['Execution', 'ExecutionStatusHistory']


class Execution(Base):
    __tablename__ = 'execution'

    __table_args__ = (
        UniqueConstraint('method_id', 'color'),
        UniqueConstraint('task_id', 'color'),
    )

    id = Column(Integer, primary_key=True)

    color = Column(Integer, index=True, nullable=False)
    parent_color = Column(Integer, index=True, nullable=True)

    method_id = Column(Integer, ForeignKey('method.id', ondelete='CASCADE'),
            index=True, nullable=True)
    task_id = Column(Integer, ForeignKey('task.id', ondelete='CASCADE'),
            index=True, nullable=True)
    _status = Column('status', Text, index=True, nullable=False)

    data = Column(MutableJSONDict, nullable=False, default=lambda:{})
    colors = Column(JSON)
    begins = Column(JSON)

    workflow_id = Column(Integer, ForeignKey('workflow.id', ondelete='CASCADE'),
        nullable=False, index=True)
    workflow = relationship('Workflow', foreign_keys=[workflow_id])

    timestamp = Column(DateTime(timezone=True), default=func.now(),
            index=True, nullable=False)

    type = Column(String, index=True, nullable=False)
    __mapper_args__ = {
            'polymorphic_on': 'type',
    }

    UPDATE_METHODS = {
        'status': 'update_status',
        'data': 'update_data',
        'outputs': 'update_outputs',
    }

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self._status = 'new'
        if self.workflow_id is not None:
            ExecutionStatusHistory(execution=self,
                    workflow_id=self.workflow_id, status='new')
        else:
            ExecutionStatusHistory(execution=self, workflow=self.workflow,
                    status='new')


    @property
    def ordered_status_history(self):
        return sorted(self.status_history, key=attrgetter('timestamp'))


    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if not statuses.is_valid(status):
            raise InvalidStatusError(
                    "Status (%s) isn't one of the valid status values: %s" %
                    (status, str(statuses.VALID_STATUSES)))
        else:
            if not statuses.is_valid_transition(self.status, status):
                LOG.debug("Refusing to change status of execution (%s) from "
                        "(%s) to (%s) in workflow %s",
                        self.name, self.status, status,
                        self.parent.workflow.name,
                        extra={'workflowName':self.parent.workflow.name})
            else:
                self.send_webhooks(status)
                self._status = status
                if self.workflow_id is not None:
                    return ExecutionStatusHistory(execution=self,
                            workflow_id=self.workflow_id, status=status)
                else:
                    return ExecutionStatusHistory(execution=self,
                            workflow=self.workflow, status=status)

    @property
    def update_timestamp(self):
        return max([h.timestamp for h in self.status_history])

    def send_webhooks(self, status):
        webhooks = self.parent.get_webhooks(status)
        if webhooks:
            # this involves at least a little overhead, so only do it once
            # we know that there are webhooks to send.
            webhook_data = {
                'workflowUrl': self.parent.workflow.url,
                'executionUrl': self.url,
                'targetName': self.parent.name,
                'targetType': self.parent.type,
                'color': self.color,
                'parentColor': self.parent_color,
                'oldStatus': self.status,
                'status': status,
            }
            for webhook in webhooks:
                webhook.send_after_commit(**webhook_data)

    def as_dict(self, detailed):
        result = {name: getattr(self, name) for name in ['name', 'color',
            'parent_color', 'data', 'colors', 'begins', 'status']}

        result['status_history'] = [h.as_dict(detailed=detailed)
                for h in self.ordered_status_history]

        if self.child_workflow_urls:
            result['childWorkflowUrls'] = self.child_workflow_urls

        if not detailed:
            result['inputs'] = self.get_inputs()
            result['outputs'] = self.get_outputs()

        return result

    def as_dict_for_executions_report(self):
        result = {name: getattr(self, name) for name in ['color',
            'colors', 'begins', 'status', 'id']}

        result['statusHistory'] = [h.as_dict()
                for h in self.ordered_status_history]
        result['parentColor'] = self.parent_color

        if self.task_id is not None:
            result['taskId'] = self.task_id
        else:
            result['methodId'] = self.method_id

        result['detailsUrl'] = self.url

        if self.child_workflow_urls:
            result['childWorkflowUrls'] = self.child_workflow_urls

        return result

    def as_dict_for_limited_report(self):
        result = {name: getattr(self, name) for name in ['color',
            'colors', 'begins', 'status', 'id']}

        result['timestamp'] = str(self.timestamp)
        result['parentColor'] = self.parent_color

        if self.task_id is not None:
            result['taskId'] = self.task_id
        else:
            result['methodId'] = self.method_id
            result['data'] = self.data.copy()
            if 'petri_response_links_for_job' in result['data']:
                del result['data']['petri_response_links_for_job']

        result['detailsUrl'] = self.url
        return result

    @property
    def child_workflow_urls(self):
        return []

    def update(self, update_data):
        old_data = self.as_dict(detailed=False)
        needs_updating = [name for name, new_value in update_data.iteritems()
                if old_data[name] != new_value]

        invalid_fields = set(needs_updating) - set(self.UPDATE_METHODS.keys())
        if (invalid_fields):
            raise ImmutableUpdateError("Cannot update the following fields: %s"
                    % invalid_fields)
        else:
            for name in needs_updating:
                getattr(self, self.UPDATE_METHODS[name])(old_data[name], update_data[name])

    def update_status(self, old_status, new_status):
        self.status = new_status

    def update_data(self, old_data, new_data):
        updated_data = old_data.copy()
        updated_data.update(new_data)
        self.data = updated_data

    def update_outputs(self, old_outputs, new_outputs):
        if (old_outputs):
            raise OutputsAlreadySet(
                    "Cannot update outputs after they have been set once")
        else:
            return self.method.task.set_outputs(outputs=new_outputs,
                    color=self.color, parent_color=self.parent_color)

    @property
    def url(self):
        return url_for('execution-detail', execution_id=self.id)

    def cancel(self):
        self.status = statuses.canceled

    def issue_job_delete_requests(self):
        pass


class ExecutionStatusHistory(Base):
    __tablename__ = 'execution_status_history'

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('execution.id',
            ondelete='CASCADE'), index=True, nullable=False)

    timestamp = Column(DateTime(timezone=True), default=func.now(),
            index=True, nullable=False)

    status = Column(Text, index=True, nullable=False)

    execution = relationship(Execution,
            backref=backref('status_history', order_by=timestamp, lazy='joined',
            passive_deletes='all'))

    workflow_id = Column(Integer, ForeignKey('workflow.id', ondelete='CASCADE'),
        nullable=False, index=True)
    workflow = relationship('Workflow', foreign_keys=[workflow_id])

    def as_dict(self, detailed=False):
        return {'timestamp': str(self.timestamp), 'status': self.status}

    def as_dict_for_limited_report(self):
        return {
                'executionId': self.execution_id,
                'timestamp': str(self.timestamp),
                'status': self.status
        }
