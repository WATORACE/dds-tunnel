#!/usr/bin/env python3
import argparse
import os
import signal
import sys
import time
from queue import Queue, Empty
from subprocess import Popen, PIPE
from threading import Thread

if os.name == 'posix':
    NDDS_HOME = '/opt/rti_connext_dds-6.0.1'
    ROUTING_SERVICE_EXEC = os.path.join(NDDS_HOME, 'bin/rtiroutingservice')
    INT_SIGNAL = signal.SIGINT
elif os.name == 'nt':
    NDDS_HOME = 'C:\\Program Files\\rti_connext_dds-6.0.1'
    ROUTING_SERVICE_EXEC = os.path.join(NDDS_HOME, 'bin\\rtiroutingservice.bat')
    INT_SIGNAL = signal.CTRL_BREAK_EVENT
else:
    raise Exception(f"Unknown os {os.name}")

try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()
TCPWANServer_CFG_FILE = os.path.join(SCRIPT_DIR, 'TCPWANServer.xml')
TCPWANClient_CFG_FILE = os.path.join(SCRIPT_DIR, 'TCPWANClient.xml')
HEARTBEAT_PY = os.path.join(SCRIPT_DIR, 'heartbeat', 'heartbeat.py')


def popen_nonblocking(*args, **kwargs):
    """
    Reliably read lines without blocking the main thread
    https://stackoverflow.com/a/4896288/4527337
    """
    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    def make_readline_nowait(q):
        def readline_nowait():
            try:
                return q.get_nowait()
            except Empty:
                return None
        return readline_nowait

    proc = Popen(*args, **kwargs)

    outQ = Queue()
    errQ = Queue()
    outT = Thread(target=enqueue_output, args=(proc.stdout, outQ), daemon=True)
    errT = Thread(target=enqueue_output, args=(proc.stderr, errQ), daemon=True)
    outT.start()
    errT.start()

    return {
        'process': proc,
        'out_readline': make_readline_nowait(outQ),
        'err_readline': make_readline_nowait(errQ),
    }


def wait_and_print_output(groupname, procs):
    """
    Waits for processes (created by Popen) to terminate and print stdout/stderr to screen
    procs is an iterable with values:
    {
        name: string,
        process: Popen,
        out_readline: () => string | None,
        err_readline: () => string | None
    }
    """
    while True:
        for proc in procs:
            output = proc['out_readline']()
            err = proc['err_readline']()

            if output:
                print(f"{groupname}: {proc['name']} (stdout): {output.decode('UTF-8').strip()}")
            if err:
                print(f"{groupname}: {proc['name']} (stderr): {err.decode('UTF-8').strip()}")

            return_code = proc['process'].poll()
            if return_code is not None:
                print(f"{groupname}: {proc['name']} exited with return code {return_code}")
                # Terminate when a process terminates
                return


def tcpwanserver(args):
    procs = []
    try:
        proc = popen_nonblocking([
            ROUTING_SERVICE_EXEC,
            '-cfgFile', TCPWANServer_CFG_FILE,
            '-cfgName', 'TCPWANServer',
            '-verbosity', '3',
            f'-DPUBLIC_ADDRESS={args.public_address}',
            f'-DINTERNAL_PORT={args.internal_port}',
            f'-DDOMAIN_ID={str(args.domain_id)}',
        ], stdout=PIPE, stderr=PIPE)
        procs.append({'name': 'routingservice', **proc})

        if not args.no_heartbeat:
            # execute the heartbeat program, -u tells python to not buffer output (otherwise no output will be shown
            # until we terminate the subprocess)
            # https://stackoverflow.com/a/107717/4527337
            heartbeat_proc = popen_nonblocking([
                sys.executable, '-u', HEARTBEAT_PY, '--domain_id', str(args.domain_id), 'responder'
            ], stdout=PIPE, stderr=PIPE)
            procs.append({'name': 'heartbeat', **heartbeat_proc})

        wait_and_print_output('tcpwanserver', procs)

    except KeyboardInterrupt:
        print('tcpwanserver: Stopping all processes...')
        for proc in procs:
            proc['process'].send_signal(INT_SIGNAL)
            wait_and_print_output('tcpwanserver', procs)


def tcpwanclient(args):
    procs = []
    try:
        env = {
            'NDDS_DISCOVERY_PEERS': ','.join(['shmem://', os.path.join('tcpv4_wan://', args.server_address)]),
        }
        routing_service_proc = popen_nonblocking([
            ROUTING_SERVICE_EXEC,
            '-cfgFile', TCPWANClient_CFG_FILE,
            '-cfgName', 'TCPWANClient',
            '-verbosity', '3',
            f'-DDOMAIN_ID={str(args.domain_id)}',
        ], env=env, stdout=PIPE, stderr=PIPE)
        procs.append({'name': 'routingservice', **routing_service_proc})

        if not args.no_heartbeat:
            # execute the heartbeat program, -u tells python to not buffer output (otherwise no output will be shown
            # until we terminate the subprocess)
            # https://stackoverflow.com/a/107717/4527337
            heartbeat_proc = popen_nonblocking([
                sys.executable, '-u', HEARTBEAT_PY, '--domain_id', str(args.domain_id), 'initiator'
            ], stdout=PIPE, stderr=PIPE)
            procs.append({'name': 'heartbeat', **heartbeat_proc})

        wait_and_print_output('tcpwanclient', procs)

    except KeyboardInterrupt:
        print('tcpwanclient: Stopping all processes...')
        for proc in procs:
            proc['process'].send_signal(INT_SIGNAL)
            wait_and_print_output('tcpwanclient', procs)


parser = argparse.ArgumentParser(description='process start-tunnel arguments')
parser.add_argument("--no-heartbeat", action='store_true',
                    help="disable heartbeat messages")
parser.add_argument("--domain_id", "-d", type=int,
                    help="The domain ID that the tunnel will be using (Default 0)", default=0)

subparsers = parser.add_subparsers(title='role', dest='role', required=True)
server_parser = subparsers.add_parser(
    'tcpwanserver', aliases=['server'], help='start a tcpwanserver (computer with at least one port exposed to the tcpwanclient)')
client_parser = subparsers.add_parser(
    'tcpwanclient', aliases=['client'], help='start a tcpwanclient (computer behind firewalls/NATs)')

server_parser.set_defaults(func=tcpwanserver)
server_parser.add_argument(
    '--internal_port', '-p', help="the internal port where the routing service will listen on (default 7400)", default=7400, required=True)
server_parser.add_argument('--public_address', '-a',
                           help="the client-accessible address where tcpwanclients can access (e.g. 1.2.3.4:7500)", required=True)

client_parser.set_defaults(func=tcpwanclient)
client_parser.add_argument('--server_address', '-a',
                           help="the address of the server (e.g. 1.2.3.4:7500)", required=True)

args = parser.parse_args()
print(args)

args.func(args)
