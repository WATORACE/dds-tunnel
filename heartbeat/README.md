# Heartbeat

## Getting Started

To initiate continuous heartbeat checks:

```bash
python3 heartbeat.py initiator
```

To listen for heartbeat messages and respond to them:

```bash
python3 heartbeat.py responder
```

To use a domain other than `0`, use the `--domain_id` param:

```bash
python3 heartbeat.py --domain_id 32 initiator
python3 heartbeat.py --domain_id 32 responder
```