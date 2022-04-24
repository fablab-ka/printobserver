import time
import re
from printer import Printer
import datetime
#from slack import RTMClient
from slack_sdk.rtm_v2 import RTMClient
import os
import threading

printers = []

# instantiate Slack client
rtm = None
if "SLACK_BOT_TOKEN" in os.environ:
	rtm = RTMClient(token=os.environ["SLACK_BOT_TOKEN"])

if rtm:
	@rtm.on("message")
	def handle(client: RTMClient, event: dict):
		if 'druckerstatus' in event['text']:
			reply = ""
			for p in printers:
				reply += p.get_status() + "\r\n"

			client.web_client.chat_postMessage(
				channel = event['channel'],
				#thread_ts = event['ts'],
				text = str(status)
			)

	def rtm_start():
		if rtm:
			rtm.start()
	t1 = threading.Thread(name='slack-daemon', target=rtm_start)
	t1.setDaemon(True)
	t1.start()

printers.append(Printer("Prusa 1", "/dev/serial/by-id/usb-Prusa_Research__prusa3d.com__Original_Prusa_i3_MK3_CZPX3119X004XK40396-if00"))
printers.append(Printer("Prusa 2", "/dev/serial/by-id/usb-Prusa_Research__prusa3d.com__Original_Prusa_i3_MK3_CZPX0219X004XK03946-if00"))
printers.append(Printer("Prusa 3", "/dev/serial/by-id/usb-Prusa_Research__prusa3d.com__Original_Prusa_i3_MK3_CZPX1719X004XK22415-if00"))


last_check = datetime.datetime.now()

while True:
	for p in printers:
		p.process()
	if (datetime.datetime.now() - last_check).seconds > 10:
		last_check = datetime.datetime.now()
		for p in printers:
			print(p.get_status())
	time.sleep(1)