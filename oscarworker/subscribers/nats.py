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

import asyncio
import os
from nats.aio.client import Client as NATS
from stan.aio.client import Client as STAN
import oscarworker.utils as utils
from oscarworker.subscribers.subscriber import Subscriber

class NatsSubscriber(Subscriber):

    cluster_id = 'faas-cluster'
    subject = 'faas-request'
    queue_group = 'faas'

    def __init__(self):
        self.client_id = 'faas-worker-{0}'.format(os.uname().nodename)

        self.nats_address = utils.get_environment_variable('NATS_ADDRESS')
        if not self.nats_address:
            self.nats_address = 'nats'

        self.nats_port = utils.get_environment_variable('NATS_PORT')
        if not self.nats_port:
            self.nats_port = '4222'


    async def run(self, loop, handler):
        # Use borrowed connection for NATS then mount NATS Streaming
        # client on top.
        nc = NATS()
        await nc.connect('{0}:{1}'.format(self.nats_address, self.nats_port), loop=loop)

        # Start session with NATS Streaming cluster.
        sc = STAN()
        await sc.connect(self.cluster_id, self.client_id, nats=nc)

        async def cb(msg):
            print('EVENT RECEIVED -----------------------------------------')
            print(msg.data)
            print('--------------------------------------------------------')
            handler(msg.data)

        await sc.subscribe(self.subject, queue=self.queue_group, cb=cb)

        # TODO: Handle SIGINT
        #await sc.close()
        #await nc.close()



