# OSCAR - On-premises Serverless Container-aware ARchitectures
# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from packaging import version
import logging
import json
import requests
import oscarworker.utils as utils
import oscarworker.eventutils as eventutils

class KubernetesClient:

    deployment_list_path = '/apis/apps/v1/namespaces/openfaas-fn/deployments/'
    create_job_path = '/apis/batch/v1/namespaces/oscar/jobs'
    nodes_info_path = '/api/v1/nodes'

    def __init__(self, token=None):
        if token:
            self.token = token
        else:
            self.token = utils.read_file('/var/run/secrets/kubernetes.io/serviceaccount/token')

        self.kubernetes_service_host = utils.get_environment_variable('KUBERNETES_SERVICE_HOST')
        if not self.kubernetes_service_host:
            self.kubernetes_service_host = 'kubernetes.default'

        self.kubernetes_service_port = utils.get_environment_variable('KUBERNETES_SERVICE_PORT')
        if not self.kubernetes_service_port:
            self.kubernetes_service_port = '443'

        self.job_ttl_seconds_after_finished = utils.get_environment_variable('JOB_TTL_SECONDS_AFTER_FINISHED')
        if not self.job_ttl_seconds_after_finished:
            self.job_ttl_seconds_after_finished = 60

    def _gen_auth_header(self):
        return {'Authorization': 'Bearer ' + self.token}

    def _create_request(self, method, url, headers=None, json=None):
        try:
            if headers is None:
                headers = {}
            headers.update(self._gen_auth_header())

            resp = requests.request(method, url, verify=False, headers=headers, json=json)
            if resp.status_code == 200:
                return resp.json()
            else:
                logging.error('Error contacting Kubernetes API: {0} - {1}'.format(resp.status_code, resp.text))
                return None
        except Exception as ex:
            logging.error('Error contacting Kubernetes API: {0}'.format(str(ex)))
            return None

    def _get_deployment_info(self, function_name):
        url = 'https://{0}:{1}{2}{3}'.format(self.kubernetes_service_host, 
                                             self.kubernetes_service_port, 
                                             self.deployment_list_path,
                                             function_name)
        deployment_info = self._create_request('GET', url)
        if not deployment_info:
            logging.error('Error getting deployment info')
            return None
        return deployment_info

    @utils.lazy_property
    def _kubernetes_version(self):
        url = 'https://{0}:{1}{2}'.format(self.kubernetes_service_host, self.kubernetes_service_port, self.nodes_info_path)
        nodes_info = self._create_request('GET', url)
        if not nodes_info:
            logging.error('Error getting nodes info')
            return None
        return version.parse(nodes_info['items'][0]['status']['nodeInfo']['kubeletVersion'])

    def _create_job_definition(self, event, function_name=None):
        event_id = eventutils.get_event_id(event)

        if not function_name:
            function_name = eventutils.get_function_name(event)

        deployment_info = self._get_deployment_info(function_name)
        container_info = deployment_info['spec']['template']['spec']['containers'][0]

        # Create JSON based on function deployment
        job = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': function_name + '-' + event_id,
                'namespace': 'oscar',
            },
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'name': container_info['name'],
                                'image': container_info['image'],
                                'command': ['supervisor'],
                                'env': container_info['env'],
                                'resources': container_info['resources']
                            }
                        ],
                        'restartPolicy': 'Never'
                    }
                }
            }
        }

        # Add event as an environment variable
        event_variable = {
            'name': 'OSCAR_EVENT',
            'value': json.dumps(event)
        }
        job['spec']['template']['spec']['containers'][0]['env'].append(event_variable)

        # Add ttlSecondsAfterFinished option if Kubernetes version is >= 1.12
        if self._kubernetes_version >= version.parse('v1.12'):
            job['spec']['ttlSecondsAfterFinished'] = self.job_ttl_seconds_after_finished

        return job

    def launch_job(self, msg_data):
        logging.info('EVENT RECEIVED -----------------------------------------')
        logging.info(msg_data)
        logging.info('--------------------------------------------------------')

        data = json.loads(msg_data.decode('utf-8'))
        event = data['Body']

        definition = self._create_job_definition(event, function_name=data['Function'])
        url = 'https://{0}:{1}{2}'.format(self.kubernetes_service_host, self.kubernetes_service_port, self.create_job_path)

        resp = self._create_request('POST', url, json=definition)
        if resp:
            logging.info('Job {0} created successfully').format(definition['metadata']['name'])