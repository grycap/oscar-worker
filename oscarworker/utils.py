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

import base64
import json
import os
import re
import subprocess
import tarfile
import tempfile
import uuid
import shutil

def copy_file(src, dst):
    shutil.copy(src, dst)

def join_paths(*paths):
    return os.path.join(*paths)

def get_temp_dir():
    return tempfile.gettempdir()

def lazy_property(func):
    ''' A decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + func.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazy_property

def find_expression(string_to_search, rgx_pattern):
    '''Returns the first group that matches the rgx_pattern in the string_to_search'''
    if string_to_search:    
        pattern = re.compile(rgx_pattern)
        match = pattern.search(string_to_search)
        if match :
            return match.group()

def base64_to_utf8_string(value):
    return base64.b64decode(value).decode('utf-8')

def utf8_to_base64_string(value):
    return base64.b64encode(value).decode('utf-8')

def dict_to_base64_string(value):
    return utf8_to_base64_string(json.dumps(value))

def divide_list_in_chunks(elements, chunk_size):
    """Yield successive n-sized chunks from th elements list."""
    if len(elements) == 0:
        yield []
    for i in range(0, len(elements), chunk_size):
        yield elements[i:i + chunk_size]
        
def get_random_uuid4_str():
    return str(uuid.uuid4())

def merge_dicts(d1, d2):
    '''
    Merge 'd1' and 'd2' dicts into 'd1'.
    'd1' has precedence over 'd2'
    '''
    for k,v in d2.items():
        if v:
            if k not in d1:
                d1[k] = v
            elif type(v) is dict:
                d1[k] = merge_dicts(d1[k], v)
            elif type(v) is list:
                d1[k] += v
    return d1

def is_value_in_dict(dictionary, value):
    return value in dictionary and dictionary[value]

def get_tree_size(path):
    """Return total size of files in given path and subdirs."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            total += get_tree_size(entry.path)
        else:
            total += entry.stat(follow_symlinks=False).st_size
    return total

def get_all_files_in_directory(dir_path):
    files = []
    for dirname, _, filenames in os.walk(dir_path):
        for filename in filenames:
            files.append(os.path.join(dirname, filename))
    return files

def get_file_size(file_path):
    '''Return file size in bytes'''
    return os.stat(file_path).st_size

def create_folder(folder_name):
    if not os.path.isdir(folder_name):
        os.makedirs(folder_name, exist_ok=True)
        
def create_file_with_content(path, content):
    with open(path, "w") as f:
        f.write(content)

def read_file(file_path, mode="r"):
    with open(file_path, mode) as content_file:
        return content_file.read()
    
def delete_file(path):
    if os.path.isfile(path):
        os.remove(path)
        
def delete_folder(folder_path):
    shutil.rmtree(folder_path)       
    
def create_tar_gz(files_to_archive, destination_tar_path):
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in files_to_archive:
            tar.add(file_path, arcname=os.path.basename(file_path))
    return destination_tar_path
      
def extract_tar_gz(tar_path, destination_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, path=destination_path)

def kill_process(self, process):
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), subprocess.signal.SIGKILL)

def execute_command(command):
    subprocess.call(command)
    
def execute_command_and_discard_output(command):
    return subprocess.call(command, stdout=subprocess.DEVNULL)    
    
def execute_command_and_return_output(command):
    return subprocess.check_output(command).decode("utf-8")

def execute_command_with_input_and_return_output(command, cmd_input):
    return subprocess.check_output(command, input=cmd_input).decode("utf-8")

def is_variable_in_environment(variable):
    return is_value_in_dict(os.environ, variable)

def set_environment_variable(key, variable):
    if key and variable:
        os.environ[key] = variable

def get_environment_variable(variable):
    if is_variable_in_environment(variable):
        return os.environ[variable]

def parse_arg_list(arg_keys, cmd_args):
    result = {}
    for key in arg_keys:
        if type(key) is tuple:
            if key[0] in cmd_args and cmd_args[key[0]]:
                result[key[1]] = cmd_args[key[0]]
        else:
            if key in cmd_args and cmd_args[key]:
                result[key] = cmd_args[key]
    return result