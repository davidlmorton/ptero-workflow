import abc
import collections
import errno
import jinja2
import json
import os
import requests
import signal
import json
import subprocess
import sys
import time
import urllib
import urlparse
import yaml


_POLLING_DELAY = 0.5
_TERMINATE_WAIT_TIME = 0.05

_MAX_RETRIES = 10
_RETRY_DELAY = 0.15


def validate_json(text):
    data = json.loads(text)


class TestCaseMixin(object):
    __metaclass__ = abc.ABCMeta

    maxDiff = None

    @property
    def api_port(self):
        return int(os.environ['PTERO_WORKFLOW_PORT'])

    @abc.abstractproperty
    def directory(self):
        pass

    @abc.abstractproperty
    def test_name(self):
        pass


    def test_got_expected_result(self):
        workflow_url = self._submit_workflow()
        self._wait_for_completion(workflow_url)
        self._verify_result(workflow_url)


    def _submit_workflow(self):
        response = _retry(requests.post, self._submit_url, self._workflow_body,
                headers={'content-type': 'application/json'})
        self.assertEqual(201, response.status_code)
        return response.headers['Location']

    def _wait_for_completion(self, workflow_url):
        max_loops = int(self._max_wait_time/_POLLING_DELAY)
        for iteration in xrange(max_loops):
            if self._workflow_complete(workflow_url):
                return
            time.sleep(_POLLING_DELAY)

    @property
    def _max_wait_time(self):
        return 20

    def _verify_result(self, workflow_url):
        actual_result = self._get_actual_result(workflow_url)
        expected_result = self._expected_result

        self.assertEqual(expected_result, actual_result)


    @property
    def _submit_url(self):
        return 'http://localhost:%d/v1/workflows' % self.api_port

    @property
    def _workflow_body(self):
        with open(self._workflow_file_path) as f:
            template = jinja2.Template(f.read())
            body = template.render(**self._template_data)
            validate_json(body)
        return body

    @property
    def _template_data(self):
        return {
            'user': os.environ.get('USER'),
            'workingDirectory': os.environ['PTERO_WORKFLOW_TEST_TEMP'],
            'environment': json.dumps(dict(os.environ)),
        }

    @property
    def _workflow_file_path(self):
        return os.path.join(self.directory, 'submit.json')

    @property
    def _expected_result(self):
        with open(self._expected_result_path) as f:
            return json.load(f)

    @property
    def _expected_result_path(self):
        return os.path.join(self.directory, 'result.json')

    def _workflow_complete(self, url):
        data = self._get_workflow_data(url)
        if data.get('status') in ['success', 'failure', 'error']:
            return True
        else:
            return False

    def _get_workflow_data(self, url):
        response = _retry(requests.get, url)
        return response.json()

    def _get_actual_result(self, workflow_url):
        data = self._get_workflow_data(workflow_url)
        response = _retry(requests.get, data['reports']['workflow-outputs'])
        return response.json()


    @property
    def _logdir(self):
        return os.path.join(self._repository_root_path, 'logs', self.test_name)

    @property
    def _repository_root_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__),
                '..', '..', '..', '..'))


def _retry(func, *args, **kwargs):
    for attempt in xrange(_MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except:
            time.sleep(_RETRY_DELAY)
    error_msg = "Failed (%s) with args (%s) and kwargs (%s) %d times" % (
            func.__name__, args, kwargs, _MAX_RETRIES)
    raise RuntimeError(error_msg)
