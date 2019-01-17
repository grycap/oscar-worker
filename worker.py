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
import logging
from oscarworker.kubernetesclient import KubernetesClient
from oscarworker.subscribers.nats import NatsSubscriber

loglevel = logging.INFO
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=loglevel)

def main():
    logging.info('Starting OSCAR Worker...')

    kube_client = KubernetesClient()
    loop = asyncio.get_event_loop()

    # Set signal handler
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, ask_exit)

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

    loop.close()
    logging.info('Closed.')

# Stop the loop after all tasks have been finished
@asyncio.coroutine
def exit():
    loop = asyncio.get_event_loop()
    loop.stop()

# Send asyncio.CancelledError exception to all tasks and close loop
def ask_exit():
    logging.info('Closing OSCAR Worker...')
    for task in asyncio.Task.all_tasks():
        task.cancel()
    asyncio.ensure_future(exit())


if __name__ == "__main__":
    main()
