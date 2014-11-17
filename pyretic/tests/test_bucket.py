################################################################################
# The Pyretic Project                                                          #
# frenetic-lang.org/pyretic                                                    #
# author: Srinivas Narayana (narayana@cs.princeton.edu)                        #
################################################################################
# Licensed to the Pyretic Project by one or more contributors. See the         #
# NOTICES file distributed with this work for additional information           #
# regarding copyright and ownership. The Pyretic Project licenses this         #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################

import argparse
import os
import subprocess, shlex
import signal
from mininet.log import setLogLevel
from mininet.topo import *
from mininet.net import Mininet
from mininet.node import CPULimitedHost, RemoteController
from mininet.cli import CLI
from pyretic.evaluations.mininet_setup import mn_cleanup, wait_switch_rules_installed, get_abort_handler

def pyretic_controller(ctlr_params, c_out, c_err, pythonpath):
    c_outfile = open(c_out, 'w')
    c_errfile = open(c_err, 'w')
    # Hackety hack. I don't know of any other way to supply the PYTHONPATH
    # variable for the pyretic controller!
    py_env = os.environ.copy()
    if not "PYTHONPATH" in py_env:
        py_env["PYTHONPATH"] = pythonpath

    cmd = ("pyretic.py -m p0 pyretic.examples.bucket " +
           reduce(lambda r, k: r + ("--" + k + "=" + ctlr_params[k] + " "),
                  ctlr_params.keys(), " "))
    c = subprocess.Popen(shlex.split(cmd), stdout=c_outfile, stderr=c_errfile,
                         env=py_env)
    return (c, c_outfile, c_errfile)

def get_mininet(topo_args, listen_port):
    """ Get a mininet network from topology arguments. """
    class_args = map(int, topo_args['class_args'].split(','))
    class_name = topo_args['class_name']
    topo = globals()[class_name](*class_args)
    net = Mininet(topo=topo, host=CPULimitedHost, controller=RemoteController,
                  listenPort=listen_port)
    net.start()
    return (net, net.hosts, net.switches)

def workload(net, hosts):
    net.pingAll()

def test_bucket_single_test():
    args = parse_args()
    test_duration_sec = args.test_duration_sec
    adjust_path = get_adjust_path(args)
    # mn_cleanup()

    """ Controller """
    c_params = {'query': args.query, 'fwding': args.fwding}
    c_out = adjust_path("pyretic-stdout.txt")
    c_err = adjust_path("pyretic-stderr.txt")
    pypath = "/home/mininet/pyretic:/home/mininet/mininet:/home/mininet/pox"
    (ctlr, c_out, c_err) = pyretic_controller(c_params, c_out, c_err, pypath)

    """ Network """
    topo_args = {'class_name': args.topo_name, 'class_args': args.topo_args}
    (net, hosts, switches) = get_mininet(topo_args, args.listen_port)

    """ Workload """
    workload(net, hosts)

    """ Finish up """
    kill_process(ctlr, "controller")
    close_fds([c_out, c_err], "controller")
    net.stop()
    
#### Helper functions #####

def get_adjust_path(args):
    """ Adjust the paths of all files relative to the global results folder. """
    results_folder = args.results_folder
    def adjust_path(rel_path):
        return os.path.join(results_folder, rel_path)
    return adjust_path

def parse_args():
    parser = argparse.ArgumentParser(description="Run correctness tests for buckets")
    parser.add_argument("--test_duration_sec", type=int,
                        help="Duration before workload finishes execution",
                        default=30)
    parser.add_argument("-q", "--query", default="test0",
                        help="Query policy to run")
    parser.add_argument("-f", "--fwding", default="mac_learner",
                        help="Forwarding policy to run")
    parser.add_argument("--topo_name", default="SingleSwitchTopo",
                        help="Topology class to use")
    parser.add_argument("--topo_args", default="3",
                        help="Arguments to the topology class constructor " +
                        "(separated by commas)")
    parser.add_argument("-l", "--listen_port", default=6634, type=int,
                        help="Starting port for OVS switches to listen on")
    parser.add_argument("-r", "--results_folder",
                        default="./pyretic/evaluations/results/",
                        help="Folder to put the raw results data into")
    args = parser.parse_args()
    return args

def kill_process(p, process_str):
    """ Kill a process """
    print "Signaling", process_str, "for completion"
    p.send_signal(signal.SIGINT)

def close_fds(fds, fd_str):
    """ Close a bunch of file descriptors """
    for fd in fds:
        fd.close()
    print "Closed", fd_str, "file descriptors"

def mn_cleanup():
    subprocess.call("sudo mn -c", shell=True)

### The main thread.
if __name__ == "__main__":
    setLogLevel('info')
    test_bucket_single_test()
