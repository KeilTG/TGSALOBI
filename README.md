Для запуска бота необходимо настроить Reverse Proxy. Например:

```bash
ssh -p 443 -L4300:127.0.0.1:4300 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -t -R0:127.0.0.1:8004 free.pinggy.io x:https
```
