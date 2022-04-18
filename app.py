import serial
import re
import datetime
#from slack import RTMClient
from slack_sdk.rtm_v2 import RTMClient
import os
import threading

# instantiate Slack client
rtm = RTMClient(token=os.environ["SLACK_BOT_TOKEN"])
# starterbot's user ID in Slack: value is assigned after the bot starts up
#starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "status"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

status = {"Hotend": 0, "Bed": 0, "File": "", "Progress": 0, "Remaining": 0, "State": "idle"}

@rtm.on("message")
def handle(client: RTMClient, event: dict):
	if 'druckerstatus' in event['text']:
		client.web_client.chat_postMessage(
			channel = event['channel'],
			#thread_ts = event['ts'],
			text = str(status)
		)
def rtm_start():
	rtm.start()

def parse_bot_commands(slack_events):
	for event in slack_events:
		if event["type"] == "message" and not "subtype" in event:
			user_id, message = parse_direct_mention(event["text"])
			if user_id == starterbot_id:
				return message, event["channel"]
	return None, None

def parse_direct_mention(message_text):
	matches = re.search(MENTION_REGEX, message_text)
	return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
	response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
	if command.startswith(EXAMPLE_COMMAND):
		response = str(status)
	slack_client.api_call("chat.postMessage", channel=channel, text=response)


skip_list = ("echo:busy", "LCD status", "SILENT MODE", "tmc2130 blabl", "0 step")
#status = {"Hotend": 0, "Bed": 0, "File": "", "Progress": 0, "Remaining": 0, "State": "idle"}


def process_line(l):
	if l.startswith(skip_list) or l == "ok":
		return
	temp = re.match("T:(\d+\.\d+) E:(\d+) B:(\d+\.\d+)", l)
	if temp:
		status["Hotend"] = temp[1]
		status["Bed"] = temp[3]
		return
	else:
		temp = re.match("T:(\d+\.\d) .*", l)
		if temp:
			status["Hotend"] = temp[1]
			return
	temp = re.match("ok T:(\d+.\d+) .* B:(\d+.\d+) .*", l)
	if temp:
		status["Hotend"] = temp[1]
		status["Bed"] = temp[2]
		return
	prog = re.match("(NORMAL|T) MODE: Percent done: (.+); print time remaining in mins: (.+); Change.*", l)
	if prog:
		status["Progress"] = prog[2]
		status["Remaining"] = prog[3]
		if prog[2] == "100" or prog[2] == "-1":
			status["State"] = "idle"
			status["File"] = ""
		#status["State"] = "printing"
		return
	file = re.match("File opened: (.*) Size: (\d+)", l)
	if file:
		status["File"] = file[1]
		status["State"] = "printing"
		return
	if l.startswith("// action:paused"):
		status["State"] = "paused"
		return
	if l.startswith("// action:resumed"):
		status["State"] = "printing"
		return
	if l.startswith("Done printing file"):
		status["State"] = "idle"
		return
	if l.startswith("echo:enqueing \"CRASH_DETECTED"):
		status["State"] = "crash"
		return
	if l.startswith("echo:enqueing \"CRASH_RECOVER"):
		status["State"] = "printing"
		return

	print(l)

t1 = threading.Thread(name='slack-daemon', target=rtm_start)
t1.setDaemon(True)
t1.start()

#if slack_client.connect(with_team_state=False):#
#	print("Starter Bot connected and running!")
#	starterbot_id = slack_client.api_call("auth.test")["user_id"]
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=10, )
print(ser.name)
last_print = datetime.datetime.now()
last_check = datetime.datetime.now()

while True:
	if ser.in_waiting > 0:
		line = ser.readline().decode("utf-8").strip()
		process_line(line)
	now = datetime.datetime.now()
	if (now - last_print).seconds > 30:
		ser.write(b"M73\r\n")
		process_line(ser.readline().decode("utf-8").strip())
		ser.write(b"M105\r\n")
		process_line(ser.readline().decode("utf-8").strip())
		print(status)
		last_print = now
#	command, channel = parse_bot_commands(slack_client.rtm_read())
#	if command:
#		handle_command(command, channel)
ser.close()
