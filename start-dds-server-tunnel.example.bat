@echo off

Rem This is an example bat file that can be used to start the dds tunnel on the "server" side (the computer that is exposed). Please replace the IP address below according to the machine configuration.

echo Please run the following in your dev environment, then press any key to continue. You should then see a continuous stream of heartbeat messages in 10 seconds.
echo ===========================================
echo python3 ./dds-tunnel/start-tunnel.py --domain_id 31 client --server_address 129.97.185.187:7400
echo ===========================================

pause

set HEARTBEAT_DOMAIN_ID=31
python3 C:\Users\IndyAdmin\Documents\dds-tunnel\start-tunnel.py --domain_id 31 server --internal_port 7400 --public_address 129.97.185.187:7400

pause