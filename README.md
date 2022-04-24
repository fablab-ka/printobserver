# printobserver
Reads the Status of Prusa i3 Mk3 Printers and pushes/displays the result in Slack

## Installation
 * Clone this repository
 * Create a new systemd service file /etc/systemd/system/printobserver.service

        [Unit]                  
        Description=Printer Service
        After=network.target
        [Service]
        Type=simple
        User=printobserver
        ExecStart=/usr/bin/python3 /home/printobserver/printobserver/app.py
        #Environment="SLACK_BOT_TOKEN=insert_token_id_here"
        [Install]
        WantedBy=multi-user.target
        
 * > systemctl daemon-reload
 * > systemctl start printobserver
 * > systemctl enable printobserver
