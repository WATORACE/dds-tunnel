# DDS Tunnel

Scripts in this file set up DDS Tunnels between machines in the current configurations (more to be added):

1. [Asymmetric NAT](#asymmetric-nat)

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
