---
language: yaml
domain: systems
type: pattern
title: systemd unit file configuration
tags: systemd, unit-file, service-configuration, systemd-service
---

# systemd Unit File Configuration

Write proper systemd service unit files for your applications.

## Basic Service Unit

```ini
[Unit]
Description=My Python Application
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=appuser
Group=appgroup
WorkingDirectory=/opt/app
Environment="PYTHONPATH=/opt/app"
ExecStart=/usr/bin/python3 /opt/app/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Timer Unit for Scheduled Tasks

```ini
[Unit]
Description=Daily cleanup task

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

## Socket-Activated Service

```ini
# myapp.socket
[Unit]
Description=My App Socket
ListenStream=/run/myapp.sock

[Socket]
Accept=no
SocketMode=0660
SocketUser=appuser

[Install]
WantedBy=sockets.target
```

```ini
# myapp.service
[Unit]
Description=My App Service
Requires=myapp.socket

[Service]
Type=notify
ExecStart=/usr/bin/python3 /opt/app/server.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Resource Limits

```ini
[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/app/main.py
MemoryMax=512M
CPUQuota=50%
LimitNOFILE=1024
LimitNPROC=50
```

## Watchdog Configuration

```ini
[Service]
Type=notify
ExecStart=/usr/bin/python3 /opt/app/main.py
WatchdogSec=30
Restart=on-failure

# If service doesn't send READY within 10s, it's killed
TimeoutStartSec=10

# If service doesn't stop within 30s, it's killed
TimeoutStopSec=30
```

## Logging Configuration

```ini
[Service]
Type=simple
ExecStart=/opt/app/run.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

# Or log to file
StandardOutput=file:/var/log/myapp/stdout.log
StandardError=file:/var/log/myapp/stderr.log
```

## Environment File

```ini
[Service]
Type=simple
EnvironmentFile=/etc/myapp/env.conf
ExecStartPre=/usr/bin/python3 -c "import sys; sys.exit(0)"
ExecStart=/usr/bin/python3 /opt/app/main.py

# env.conf contents:
# API_KEY=secret123
# LOG_LEVEL=INFO
# DATABASE_URL=postgresql://localhost/db
```

## Multi-Instance Service

```ini
[Unit]
Description=My App Instance %i
After=network.target

[Service]
Type=simple
Environment=INSTANCE_ID=%i
ExecStart=/opt/app/run.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# Enable instances
systemctl enable myapp@1
systemctl enable myapp@2
```

This pattern creates reliable systemd services.