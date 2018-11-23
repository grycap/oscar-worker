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
import signal
import oscarworker.utils as utils
from oscarworker.kubernetesclient import KubernetesClient
from oscarworker.subscribers.nats import NatsSubscriber

def main():
    print('Starting OSCAR Worker...')

    token = utils.get_environment_variable('KUBE_TOKEN')
    kube_client = KubernetesClient(token=token)
    loop = asyncio.get_event_loop()

    # Set signal handler
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, exit)

    # Subscribers list (Currently only nats)
    subscribers = []
    nats_client = NatsSubscriber()
    subscribers.append(nats_client)
    
    # Asyncio tasks list
    tasks = []
    for subscriber in subscribers:
        #task = asyncio.create_task(subscriber.run(loop, kube_client.launch_job)) # Only works in Python 3.7+
        task = asyncio.ensure_future(subscriber.run(loop, kube_client.launch_job))
        tasks.append(task)

    # Run tasks
    loop.run_until_complete(asyncio.wait(tasks))
    loop.run_forever()

# Send asyncio.CancelledError exception to all tasks
def exit():
    for task in asyncio.Task.all_tasks():
        task.cancel()
    asyncio.get_running_loop().close()


if __name__ == "__main__":
    main()
