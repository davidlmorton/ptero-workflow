from ..base import BaseAPITest
import time
from pprint import pformat
import os
from ptero_common import statuses


class TestSimpleWorkflow(BaseAPITest):
    @property
    def post_data(self):
        return {
                'tasks': {
                    'A': {
                        'methods': [
                            {
                                'name': 'execute',
                                'service': 'shell-command',
                                'parameters': {
                                    'commandLine': ['./echo_command'],
                                    'user': os.environ.get('USER'),
                                    'workingDirectory': os.environ['PTERO_WORKFLOW_TEST_SCRIPTS_DIR'],
                                    'environment': dict(os.environ),
                                    }
                                }
                            ]
                        },
                    },
                'links': [
                    {
                        'source': 'input connector',
                        'destination': 'A',
                        'sourceProperty': 'in_a',
                        'destinationProperty': 'param',
                        },
                    {
                        'source': 'A',
                        'destination': 'output connector',
                        'sourceProperty': 'param',
                        'destinationProperty': 'out_a',
                        },
                    ],
                'inputs': {
                    'in_a': 'kittens',
                    },
                'name': 'simple-workflow',
                }


    def test_execution_endpoint(self):
        post_response = self.post(self.post_url, self.post_data)

        self.assertEqual(201, post_response.status_code)

        for i in range(20):
            if (self.workflow_is_succeeded(post_response)):
                executions_response = self.get(
                        post_response.json()['urls']['executions'])
                self.assertEqual(200, executions_response.status_code)
                self.assertEqual(len(executions_response.json()['executions']), 6)
                return
            else:
                time.sleep(1)
        self.assertTrue(False, "Workflow timed out")

    def workflow_is_succeeded(self, post_response):
        status_url = post_response.json()['reports']['workflow-status']
        status_response = self.get(status_url)
        return status_response.json()['status'] == statuses.succeeded

