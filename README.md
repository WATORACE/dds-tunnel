# DDS Tunnel

Set up DDS Tunnels between computers behind NATs.

1. [Asymmetric NAT](#asymmetric-nat)
1. [Symmetric NAT](#symmetric-nat)

### Asymmetric NAT

This configuration is for two computers behind NATs (or firewalls), where one can port-forward a single port to be accessed by the other computer.

This correspond to the configuration described in the "Asymmetric Communication Across NATs" section of the [RTI Routing Service 5.3.1 Manual][rti-5.3.1-manual-pdf].

[rti-5.3.1-manual-pdf]: https://community.rti.com/static/documentation/connext-dds/5.3.1/doc/manuals/routing_service/RTI_Routing_Service_UsersManual.pdf

#### Example:

Computers `A`, `B` are behind NATs. `A` can port forward its internal port 7500 to router port 7400 for `B` to access. The `B`-accessible IP address of `A` is `1.2.3.4`.

Run this on `A`:

```bash
python3 start-tunnel.py server --internal_port=7500 --public_address=1.2.3.4:7400
```

Run this on `B`:

```bash
python3 start-tunnel.py client --server_address=1.2.3.4:7400
```

#### Custom Domain ID

To use a domain other than `0`, use the `--domain_id` param:

```bash
python3 start-tunnel.py --domain_id 31 server --internal_port=7500 --public_address=1.2.3.4:7400
python3 start-tunnel.py --domain_id 31 client --server_address=1.2.3.4:7400
```

#### Heartbeat

Heartbeats are sent from `TCPWANClient` to `TCPWANServer` periodically to check the health and latency of the connection. If you'd like to disable the heartbeat feature, add `--no-heartbeat` to the end of the script invocation.


### Symmetric NAT

This configuration is for two computers behind firewalls that do not support port-forwarding. This setup **requires a relay bridge** accessible by both computers.

#### Example

Relay Bridge:

Suppose that we have a bridge set up at `172.31.93.114` that exposes ports `7500` and `7501`.

Run this on one computer. This will connect domain 50 with the relay bridge:

```bash
python3 rti/dds-tunnel/start-tunnel.py --domain_id 50 client --server_address 172.31.93.114:7500 --heartbeat_type initiator
```

Run this on the other computer. This will connect domain 35 with the relay bridge:

```bash
python3 rti/dds-tunnel/start-tunnel.py --domain_id 35 client --server_address 172.31.93.114:7501 --heartbeat_type responder
```

- The `--heartbeat_type` parameter is interchangeable, as long as one of them is an initiator and the other a responder.

