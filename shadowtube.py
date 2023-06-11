#!/usr/bin/python3

### Dependencies

from __future__ import print_function
import itertools, threading, subprocess
import socket, shutil
import time, json, html
import sys
import re, io, os

try:
	from lxml.cssselect import CSSSelector
	from stem.control import Controller
	from requests import get
	from stem import Signal
	from stem.connection import IncorrectPassword
	from stem import SocketError
	import lxml.html
	import requests
	import argparse
	import socket
	import socks
except ImportError:
	print("Erro: Dependency failure. Installing packages...")
	subprocess.check_call([sys.executable, '-m', 'pip', '-r', 'install', 'requirements.txt'])
	print("Done.")
	sys.exit(1)

### Global variables/Settings

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v={youtube_id}"
YOUTUBE_COMMENTS_AJAX_URL = "https://www.youtube.com/comment_service_ajax"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"

settings_dict = None
with open('/etc/shadowtube/settings.json') as f:
	settings_dict = json.load(f);

use_control_pass = settings_dict["use_control_pass"]
control_pass = settings_dict["control_pass"]
control_port = settings_dict["control_port"]
socks_port = settings_dict["socks_port"]

### Tor

def tor_authenticate():
	s = requests.Session()
	s.proxies = {"http": "socks5://localhost:" + str(socks_port), "https": "socks5://localhost:" + str(socks_port)}
	return s

def tor_rotate():
	time.sleep(10)
	try:
		with Controller.from_port(port = 9151) as c:
			if use_control_pass:
				c.authenticate(password = control_pass)
				c.signal(Signal.NEWNYM)
			else:
				c.authenticate()
				c.signal(Signal.NEWNYM)
	except IncorrectPassword:
		print("Error: Failed to authenticate. Control port password incorrect.")
		sys.exit(1)
	except SocketError:
		print("Error: Connection refused. Ensure cookie authentication/control port are enabled.")
		sys.exit(1)

def tor_validate():
	att = 0
	print("Reaching Tor service...")
	while True:
		try:
			tor_authenticate().get("https://ip.seeip.org")
			print("Success")
			time.sleep(1.2)
			os.system("clear")
			break
		except IOError:
			print("Error: Failed to establish conection. Trying again in 5 seconds.")
			att += 1
			time.sleep(5)
			if att == 10:
				print("User idle. Exiting.")
				sys.exit(1)

### Output

def out_geoip():
	try:
		r = tor_authenticate().get("https://ip.seeip.org/geoip")
		r_dict = r.json()
		print(r_dict["country"] + " — " + r_dict["ip"])
	except IOError:
		print("Unknown")

def out_conclude(att, acc):
	if att == 0:
		print("\nInterrupted before granted sufficient time")
	elif acc == 0 and att > 0:
		print("\nAlarming behavior detected")
	elif att > acc:
		print("\nQuestionable behavior detected")
	elif att == acc and att > 0:
		print("\nNo abnormal behavior detected")

### Video - https://www.youtube.com/watch?v=Y6ljFaKRTrI

def video_init(youtube_id):
	att = 0
	acc = 0
	url = "https://www.youtube.com/watch?v=" + youtube_id
	try:
		while True:
			try:
				page_data = tor_authenticate().get(url).text
				parse_title = str(re.findall('<title>(.*?) - YouTube</title><meta name="title" content=', page_data))
				title = html.unescape(parse_title.split("'")[1])
				break
			except IndexError:
				tor_rotate()
		if title == "":
			print("\nVideo unavailable")
			sys.exit(1)
		else:
			print("\n" + title)
		print("Interrupt (CTRL+C) to conclude the session\n")
		while True:
			tor_rotate()
			q = tor_authenticate().get("https://www.youtube.com/results?search_query=" + "+".join(title.split())).text
			if q.find('"title":{"runs":[{"text":"') >= 0:
				if q.find(title) >= 0:
					acc += 1
					print("[✓]", end=" ")
				else:
					print("[x]", end=" ")
				out_geoip()
				att += 1
		out_conclude(att, acc)
	except KeyboardInterrupt:
		out_conclude(att, acc)

### Comments - https://www.youtube.com/feed/history/comment_history
### Comment url template (removed) - https://www.youtube.com/watch?v=OfsojVaqyAA&lc=Ugx5BtG_-N5pwDyvOiF4AaABAg.9NEWMl2CCJR9NI73GZeCDa

def comments_init():
	att = 0
	acc = 0
	ind = 1
	print("\nInterrupt (CTRL+C) to conclude the session")
	try:
		with io.open("Google - My Activity.html", "r", encoding = "utf-8") as raw_html:
			html = raw_html.read().replace("\n", "").replace("'", "`")
			text_list = str(re.findall('<div class="QTGV3c" jsname="r4nke">(.*?)</div><div class="SiEggd">', html))
			uuid_list = str(re.findall('data-token="(.*?)" data-date', html))
			url_list = str(re.findall('<div class="iXL6O"><a href="(.*?)" jslog="65086; track:click"', html))
			for i in range(int(url_list.count("'") / 2)):
				text = text_list.split("'")[ind]
				uuid = uuid_list.split("'")[ind]
				url = url_list.split("'")[ind]
				comment_url = url + "&lc=" + uuid
				ins = 0
				ind += 2
				print('\n"' + text.replace("`", "'") + '"')
				print(url + "\n")
				for i in range(0, 3, 1):
					comments_fetch(url.replace("https://www.youtube.com/watch?v=", ""))
					if private == True:
						break
					with open("temp.json", "r") as json:
						j = json.read()
						if j.find(uuid) >= 0:
							print("[✓]", end=" ")
							ins += 1
						else:
							print("[x]", end=" ")
							if ins > 0:
								ins -= 1
						out_geoip()
					tor_rotate()
				if private == False:
					if ins == 3:
						acc += 1
					attempts += 1
		out_conclude(att, acc)
	except KeyboardInterrupt:
		out_conclude(att, acc)

def comments_fetch(youtube_id):
	parser = argparse.ArgumentParser()
	try:
		args, unknown = parser.parse_known_args()
		output = "temp.json"
		limit = 1000
		if not youtube_id or not output:
			parser.print_usage()
			raise ValueError('Error: Faulty video I.D.')
		if os.sep in output:
			if not os.path.exists(outdir):
				os.makedirs(outdir)
		count = 0
		with io.open(output, 'w', encoding='utf8') as fp:
			for comment in comments_download(youtube_id):
				comment_json = json.dumps(comment, ensure_ascii=False)
				print(comment_json.decode('utf-8') if isinstance(comment_json, bytes) else comment_json, file=fp)
				count += 1
				if limit and count >= limit:
					break
	except Exception as e:
		print('Error:', str(e))
		sys.exit(1)

def find_value(html, key, num_chars=2, separator='"'):
	pos_begin = html.find(key) + len(key) + num_chars
	pos_end = html.find(separator, pos_begin)
	return html[pos_begin: pos_end]

def ajax_request(session, url, params=None, data=None, headers=None, retries=5, sleep=20):
	for _ in range(retries):
		response = session.post(url, params=params, data=data, headers=headers)
		if response.status_code == 200:
			return response.json()
		if response.status_code in [403, 413]:
			return {}
		else:
			time.sleep(sleep)

def comments_download(youtube_id, sleep=.1):
	global private
	private = False
	session = requests.Session()
	session.headers['User-Agent'] = USER_AGENT

	response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
	html = response.text

	session_token = find_value(html, 'XSRF_TOKEN', 3)
	session_token = session_token.encode('ascii').decode('unicode-escape')

	data = json.loads(find_value(html, 'var ytInitialData = ', 0, '};') + '}')
	for renderer in search_dict(data, 'itemSectionRenderer'):
		ncd = next(search_dict(renderer, 'nextContinuationData'), None)
		if ncd:
			break
	try:
		if not ncd:
			private = False
			return
	except UnboundLocalError:
		private = True
		print("Private video")
		return
	continuations = [(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comments')]
	while continuations:
		continuation, itct, action = continuations.pop()
		response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL,
								params={action: 1,
										'pbj': 1,
										'ctoken': continuation,
										'continuation': continuation,
										'itct': itct},
								data={'session_token': session_token},
								headers={'X-YouTube-Client-Name': '1',
										'X-YouTube-Client-Version': '2.20201202.06.01'})

		if not response:
			break
		if list(search_dict(response, 'externalErrorMessage')):
			raise RuntimeError('Error returned from server: ' + next(search_dict(response, 'externalErrorMessage')))

		if action == 'action_get_comments':
			section = next(search_dict(response, 'itemSectionContinuation'), {})
			for continuation in section.get('continuations', []):
				ncd = continuation['nextContinuationData']
				continuations.append((ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comments'))
			for item in section.get('contents', []):
				continuations.extend([(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comment_replies')
									for ncd in search_dict(item, 'nextContinuationData')])

		elif action == 'action_get_comment_replies':
			continuations.extend([(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comment_replies')
								for ncd in search_dict(response, 'nextContinuationData')])

		for comment in search_dict(response, 'commentRenderer'):
			yield {'cid': comment['commentId'],'text': ''.join([c['text'] for c in comment['contentText']['runs']])}

		time.sleep(sleep)

def search_dict(partial, search_key):
	stack = [partial]
	while stack:
		current_item = stack.pop()
		if isinstance(current_item, dict):
			for key, value in current_item.items():
				if key == search_key:
					yield value
				else:
					stack.append(value)
		elif isinstance(current_item, list):
			for value in current_item:
				stack.append(value)

### Init

def main():
	parser = argparse.ArgumentParser(description="A YouTube shadowban detection program.")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-v", "--video", help="analyze individual video URLs", action="store_true")
	group.add_argument("-c", "--comments", help="analyze locally available comment history", action="store_true")
	args = parser.parse_args()
	if args.video:
		tor_validate()
		while True:
			print("Complete the video URL in question")
			youtube_id = input("https://www.youtube.com/watch?v=")
			count = 0
			for c in youtube_id:
				if c.isspace() != True:
					count = count + 1
			if count == 11:
				response = tor_authenticate().get("https://www.youtube.com/watch?v=" + youtube_id)
				break
			else:
				os.system("clear")
		video_init(youtube_id)
	elif args.comments:
		tor_validate()
		while True:
			try:
				print('The basic HTML page data from https://www.youtube.com/feed/history/comment_history must be locally available to the script as "Google - My Activity.html"')
				confirm = input("Confirm? (Y) ")
				if confirm == "Y" or confirm == "y":
					try:
						io.open("Google - My Activity.html", "r")
						break
					except IOError:
						print("Error: File does not exist.")
				elif confirm == "N" or confirm == "n":
					print("Exiting.")
					sys.exit(1)
				else:
					os.system("clear")
			except ValueError:
				continue
		comments_init()
	else:
		os.system("python3 shadowtube.py -h")

if __name__ == "__main__":
	main()