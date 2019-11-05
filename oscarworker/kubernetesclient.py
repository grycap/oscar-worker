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
import uuid
import os.path
import requests
import oscarworker.utils as utils

class KubernetesClient:

    deployment_list_path = '/apis/apps/v1/namespaces/openfaas-fn/deployments/'
    create_job_path = '/apis/batch/v1/namespaces/oscar-fn/jobs'
    nodes_info_path = '/api/v1/nodes'

    def __init__(self):
        self.token = utils.get_environment_variable('KUBE_TOKEN')
        if not self.token:
            self.token = utils.read_file('/var/run/secrets/kubernetes.io/serviceaccount/token')

        if os.path.isfile('/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'):
            self._cert_verify = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
        else:
            self._cert_verify = False

        self.kubernetes_service_host = utils.get_environment_variable('KUBERNETES_SERVICE_HOST')
        if not self.kubernetes_service_host:
            self.kubernetes_service_host = 'kubernetes.default'

        self.kubernetes_service_port = utils.get_environment_variable('KUBERNETES_SERVICE_PORT')
        if not self.kubernetes_service_port:
            self.kubernetes_service_port = '443'

        self.job_ttl_seconds_after_finished = utils.get_environment_variable('JOB_TTL_SECONDS_AFTER_FINISHED')
        if not self.job_ttl_seconds_after_finished:
            self.job_ttl_seconds_after_finished = 60

        self.job_backoff_limit = utils.get_environment_variable('JOB_BACKOFF_LIMIT')
        if not self.job_backoff_limit:
            self.job_backoff_limit = 6

    def _gen_auth_header(self):
        return {'Authorization': 'Bearer ' + self.token}

    def _create_request(self, method, url, headers=None, json=None):
        try:
            if headers is None:
                headers = {}
            headers.update(self._gen_auth_header())

            resp = requests.request(method, url, verify=self._cert_verify, headers=headers, json=json)
            if resp.status_code in [200, 201, 202]:
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

    def _create_job_definition(self, function_name, event, envs):
        deployment_info = self._get_deployment_info(function_name)
        container_info = deployment_info['spec']['template']['spec']['containers'][0]

        # Volumes
        pod_spec = deployment_info['spec']['template']['spec']
        if 'volumes' in pod_spec:
            volumes = pod_spec['volumes']
        else:
            volumes = []

        # Set default resources if they are not specified in the deployment
        if 'resources' in container_info and bool(container_info['resources']):
            resources = container_info['resources']
        else:
            resources = {
                'requests': {
                    'memory': '256Mi',
                    'cpu': '250m'
                },
                'limits': {
                    'memory': '256Mi',
                    'cpu': '250m'
                }
            }

        # Create JSON based on function deployment
        job = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': '{0}-{1}'.format(function_name, str(uuid.uuid4())),
                'namespace': 'oscar-fn',
            },
            'spec': {
                'backoffLimit': int(self.job_backoff_limit),
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'name': container_info['name'],
                                'image': container_info['image'],
                                'command': ['/bin/sh'],
                                'args': ['-c', 'echo $EVENT | $fprocess'],
                                'env': container_info['env'] if 'env' in container_info else [],
                                'resources': resources,
                                'volumeMounts': container_info['volumeMounts'] if 'volumeMounts' in container_info else []
                            }
                        ],
                        'volumes': volumes,
                        'restartPolicy': 'OnFailure'
                    }
                }
            }
        }

        # Add event as an environment variable
        event_variable = {
            'name': 'EVENT',
            'value': str(event)
        }
        job['spec']['template']['spec']['containers'][0]['env'].append(event_variable)

        # Add additional environment variables
        job['spec']['template']['spec']['containers'][0]['env'].extend(envs)

        # Add ttlSecondsAfterFinished option if Kubernetes version is >= 1.12
        if self._kubernetes_version >= version.parse('v1.12'):
            job['spec']['ttlSecondsAfterFinished'] = int(self.job_ttl_seconds_after_finished)

        return job

    def _create_additional_envs(self, data):
        envs = []
        if utils.is_value_in_dict(data, 'Host'):
            envs.append({'name': 'Http_Host', 'value': data['Host']})
        if utils.is_value_in_dict(data, 'Path'):
            envs.append({'name': 'Http_Path', 'value': data['Path']})
        if utils.is_value_in_dict(data, 'QueryString'):
            envs.append({'name': 'Http_Query', 'value': data['QueryString']})
        if utils.is_value_in_dict(data, 'Header'):
            headers = data['Header']
            for key, value in headers.items():
                name = 'Http_{0}'.format(key.replace('-', '_'))
                envs.append({'name': name, 'value': value[0]})
        return envs

    def launch_job(self, data):
        function_name = data['Function']
        # Decode data body (OpenFaaS Gateway encodes it to base64)
        event = utils.base64_to_utf8_string(data['Body'])

        logging.info('EVENT RECEIVED: {0}'.format(event))

        # Create additional environment variables
        envs = self._create_additional_envs(data)

        definition = self._create_job_definition(function_name, event, envs)
        url = 'https://{0}:{1}{2}'.format(self.kubernetes_service_host, self.kubernetes_service_port, self.create_job_path)
        resp = self._create_request('POST', url, json=definition)
        if resp:
            logging.info('Job {0} created successfully'.format(definition['metadata']['name']))
