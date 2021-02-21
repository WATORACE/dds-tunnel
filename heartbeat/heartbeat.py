import argparse
import asyncio
import os
import rticonnextdds_connector as rti
import sys
import threading
from enum import IntEnum
from time import sleep, time

try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

DOMAIN_ID_ENV_VAR = 'HEARTBEAT_DOMAIN_ID'
# rti connector is not thread-safe. Using an Rlock to create mutual-exclusively between threads
# https://community.rti.com/static/documentation/connector/1.0.0/api/python/threading.html
connector_lock = threading.RLock()

class MessageType(IntEnum):
    """
    The type of the heartbeat. This must be synchronized with Heartbeat.xml.
    """
    HEARTBEAT = 0
    ACK = 1


async def publishHeartbeat(writer, writelog, period=1):
    """
    In a loop: publish heartbeat, then wait `period` seconds
    """
    current_seq = 0
    while True:
        print(f"Sending heartbeat seq {current_seq}")
        with connector_lock:
            writer.instance.set_number("seq", current_seq)
            writer.instance.set_number("type", MessageType.HEARTBEAT)
            writelog[current_seq] = time()
            writer.write()
        current_seq += 1
        await asyncio.sleep(period)


async def subscribeToAck(reader, writelog):
    while True:
        current_time = time()
        with connector_lock:
            reader.take()
            for sample in reader.samples.valid_data_iter:
                msg_type = sample.get_number('type')
                seq = int(sample.get_number("seq"))
                if msg_type != MessageType.ACK:
                    continue
                outgoing_time = writelog.get(seq)
                del writelog[seq]

                if outgoing_time is None:
                    print(f"ACK: seq {seq}")
                else:
                    print(f"ACK: seq {seq}, roundtrip time: {(current_time - outgoing_time) * 1000:.2f} ms")
        await asyncio.sleep(0.001)


async def run(*coroutines):
    await asyncio.gather(*coroutines)


def initiator(reader, writer):
    # TODO: writelog does not remove old entries. This will continue to eat up memory.
    writelog = {}

    writer_coroutine = publishHeartbeat(writer, writelog)
    reader_coroutine = subscribeToAck(reader, writelog)
    runnable = run(writer_coroutine, reader_coroutine)

    asyncio.run(runnable)


def responder(reader, writer):
    while True:
        try:
            reader.wait(500)  # milliseconds
        except rti.TimeoutError:
            pass
        with connector_lock:
            reader.take()
            for sample in reader.samples.valid_data_iter:
                msg_type = sample.get_number('type')
                seq = int(sample.get_number("seq"))
                if msg_type != MessageType.HEARTBEAT:
                    continue
                print(f"HEARTBEAT: seq {seq}")
                writer.instance.set_number("seq", seq)
                writer.instance.set_number("type", MessageType.ACK)
                writer.write()


def main():
    parser = argparse.ArgumentParser(description='process start-tunnel arguments')
    parser.add_argument("action", choices=["initiator", "responder"])
    parser.add_argument("--domain_id", "-d", type=int,
                        help="The domain ID where the heartbeat will be sent/read from (Default 0)", default=0)
    args = parser.parse_args()
    print(args)

    if os.name == 'nt':
        # Setting os.environ does not propagate env into the connector on Windows. Prompt user to manually set the env.
        env_domain_id = os.getenv(DOMAIN_ID_ENV_VAR)
        if env_domain_id != str(args.domain_id):
            sys.exit("Automatically setting domain_id in Windows is not supported. Please run `set {}={}` in cmd.exe (current value is {})".format(
                DOMAIN_ID_ENV_VAR, args.domain_id, env_domain_id))
    else:
        os.environ[DOMAIN_ID_ENV_VAR] = str(args.domain_id)

    with rti.open_connector(
            config_name="HeartbeatParticipantLibrary::HeartbeatParticipant",
            url=os.path.join(SCRIPT_DIR, "Heartbeat.xml")) as connector:

        writer = connector.get_output("HeartbeatPublisher::HeartbeatWriter")
        reader = connector.get_input("HeartbeatSubscriber::HeartbeatReader")

        try:
            print(f"Starting {args.action} on domain {os.getenv(DOMAIN_ID_ENV_VAR)}")
            if args.action == 'initiator':
                initiator(reader, writer)
            elif args.action == 'responder':
                responder(reader, writer)
            else:
                print(f"Unknown command {args.action}")
        except KeyboardInterrupt:
            print("Stopping...")


if __name__ == '__main__':
    main()
