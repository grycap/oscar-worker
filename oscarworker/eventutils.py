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

import json
import oscarworker.utils as utils

def is_cloudevent(event):
    if 'eventID' in event and 'data' in event:
        return True
    else:
        return False

def extract_cloudevent(event):
    return event['data']['body']

def get_function_name(event):
    if is_cloudevent(event):
        event = extract_cloudevent(event)
    # remove '-in'
    return event["Records"][0]["s3"]["bucket"]["name"][:-3]

def get_event_id(event):
    if is_cloudevent(event):
        return event['eventID']
    else:
        return str(uuid.uuid4())