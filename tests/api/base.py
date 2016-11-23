import requests
import json
import os
import subprocess
import time
import unittest
import crier
from crier.script import Script

__all__ = ['BaseAPITest']



class BaseAPITest(unittest.TestCase):
    def setUp(self):
        self.api_host = os.environ['PTERO_WORKFLOW_HOST']
        self.api_port = int(os.environ['PTERO_WORKFLOW_PORT'])

    def create_webhook_server(self, response_codes):
        scripts = [Script(status_code=rc) for rc in response_codes]
        server = crier.Webserver(scripts=scripts)
        server.start()
        return server

    @property
    def base_url(self):
        return 'http://%s:%s' % (self.api_host, self.api_port)

    @property
    def post_url(self):
        return '%s/v1/workflows' % self.base_url

    @property
    def get_url(self):
        return self.post_url

    def get(self, url, **kwargs):
        return _deserialize_response(requests.get(url, params=kwargs))

    def patch(self, url, data):
        return _deserialize_response(requests.patch(url,
            headers={'content-type': 'application/json'},
            data=json.dumps(data)))

    def post(self, url, data):
        return _deserialize_response(requests.post(url,
            headers={'content-type': 'application/json'},
            data=json.dumps(data)))

    def put(self, url, data):
        return _deserialize_response(requests.put(url,
            headers={'content-type': 'application/json'},
            data=json.dumps(data)))

    def delete(self, url, data=None):
        if data is not None:
            return _deserialize_response(requests.delete(url,
                headers={'content-type': 'application/json'},
                data=json.dumps(data)))
        else:
            return _deserialize_response(requests.delete(url))


def _deserialize_response(response):
    try:
        response.DATA = response.json()
    except ValueError:
        print "No JSON could be decoded from response to %s %s" % (
                response.request.method, response.request.url)
    return response
