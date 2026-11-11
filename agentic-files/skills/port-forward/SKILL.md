---
name: port-forward
description: "Forward a TCP port on this machine to another ip and port with socat: listen on <bind-ip>:<port>, relay to <target-ip>:<target-port>. Load it when arpad says 'port forward X', 'forward port N to host:M', 'let me reach X from here', or needs a service on one network (LAN box, router page, container, vpn peer) reachable on an address of this machine he can get to. A plain TCP relay - any password is typed by him on his own device, never through the agent."
---

# port-forward: relay ip:port to ip:port

socat listens on an address of this machine and pipes bytes to a target. it is a raw TCP relay, so
TLS runs end to end between his client and the target - nothing is decrypted here, and a login he
types never reaches the agent.

## start

```
socat TCP-LISTEN:<port>,bind=<bind-ip>,reuseaddr,fork TCP:<target-ip>:<target-port>
```

- `<bind-ip>` is the interface he will connect from: the address on the network he is on (`ip -4
  addr` lists them; a vpn or overlay address is one of them). bind to that one address, never
  `0.0.0.0`, unless he asks for every interface - each extra interface exposes the target further.
- `<port>` is above 1024 unless running as root; any free port works.
- run it with `run_in_background`, one socat per forwarded port.
- check it listens before handing him the address:
  `timeout 3 bash -c "</dev/tcp/<bind-ip>/<port>" && echo up`.

## web pages: forward https, not http

most routers and appliances answer http with a redirect to `https://<host>/` on the default port,
which drops the forwarded port and fails. forward the target's https port and hand him the https
address directly:

```
socat TCP-LISTEN:8443,bind=<bind-ip>,reuseaddr,fork TCP:<target-ip>:443
```

he opens `https://<bind-ip>:8443` and accepts the self-signed certificate warning. forward http
only for a target that serves plain http and does not redirect.

## stop

stop every forward when he is done - an idle one leaves the target reachable.

```
kill $(pgrep -f '^socat TCP-LISTEN:<port>')   # one forward
pkill -x socat                                # every socat on the box
```

`pkill -f '<pattern>'` run through the Bash tool also matches the wrapping shell, whose command line
holds the same pattern, and kills it: anchor with `^socat` or use `pgrep`/`kill`. confirm with
`pgrep -a socat`.

## rules

- never ask for, type or store the target's password; he logs in on his own device.
- never put a real ip, hostname or device name into this skill or any tracked file - they belong in
  the command he runs and nowhere else.
- a forward is outward-facing: start it when he asks, and tell him when it is up and when it is
  stopped.
