#!/usr/bin/env python3

from __future__ import print_function
import os
import subprocess
import datetime

class InvalidSetupError(Exception): pass

TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
DEFAULT_LOG = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", f"deploy_log_{TIMESTAMP}.txt")
def log(indentation, message, quiet=False):
    if quiet:
        return
    indent_str = ""
    while indentation > 1:
        indent_str += "|  "
        indentation -= 1
    if indentation == 1:
        indent_str += "|- "
    print(indent_str + message)

def create_log_fn(base_indentation, base_log=log, quiet=False):
    if quiet:
        return lambda indentation, message: 0
    else:
        return lambda indentation, message: base_log(base_indentation + indentation, message)

def execute_command_quietly(command_line_list):
    """Executes a command, given as a list, while supressing any output."""
    with open(os.devnull, "wb") as devnull:
        subprocess.check_call(command_line_list, stdout=devnull, stderr=subprocess.STDOUT)

def execute_command_log(command_line_list, log_file_name=DEFAULT_LOG):
    with open(log_file_name, "ab") as logfile:
        logfile.write(f"\nExecuting: {' '.join(command_line_list)}\n".encode())
        subprocess.check_call(command_line_list, stdout=logfile, stderr=subprocess.STDOUT)

def execute_command_for_output(command_line_list):
    return subprocess.Popen(command_line_list, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")

