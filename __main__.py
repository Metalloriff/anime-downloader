import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import platform
from os import path, system
from html import unescape

if platform.system() == "Linux":
	import readline

import requests
from alive_progress import alive_bar
from pick import pick

clear = lambda: system("cls" if sys.platform == "win32" else "clear")

def argument(arg, default = None):
	if arg in sys.argv:
		return sys.argv[sys.argv.index(arg) + 1]
	return default

api = "https://animension.to/public-api"

clear()
name = argument("--name") or input("Search anime: ")

clear()
dub = "--dub" in sys.argv
sub = "--sub" in sys.argv

def get_sub_dub():
	global sub
	global dub

	if not dub and not sub:
		try:
			_, index = pick(["Subbed", "Dubbed"], "Select audio/subtitle type:", indicator=">>")
			sub = index == 0
			dub = index == 1
		except KeyboardInterrupt:
			exit()
get_sub_dub()

filtering = ""
if sub:
	filtering = "&dub=0"
elif dub:
	filtering = "&dub=1"

def fetch_episodes():
	return json.loads(requests.get(f"{api}/search.php?search_text={name}&page=1&sort=az{filtering}").content)

clear()
results = fetch_episodes()

def select_anime():
	global name
	global results

	try:
		if len(results) == 0:
			_, index = pick(["Go back", "Exit"], "No results found.", indicator=">>")

			if index == 0:
				clear()
				name = input("Search anime: ")
				results = fetch_episodes()
				return select_anime()
			if index == 1:
				exit()

		_, index = pick(["Go back"] + [unescape(x["0"] if isinstance(x, dict) else x[0]) for x in results], "Select anime:", indicator=">>")

		if index == 0:
			clear()
			name = input("Search anime: ")
			results = fetch_episodes()
			return select_anime()
		
		return results[index - 1]
	except KeyboardInterrupt:
		exit()
	
anime, id, cover, _ = select_anime()
episodes = json.loads(requests.get(f"{api}/episodes.php?id={id}").content)[::-1]

clear()

defaultDir = re.sub(r"[^\s\w\d-]", "", anime)
fp = path.join(os.getcwd(), defaultDir)

def get_path():
	try:
		print("Please enter the path you'd like to download to, or press enter to save to default directory...")
		print("Default directory: " + fp)
		print()

		p = ""

		# Thanks, Linux, for being a usable operating system.
		if platform.system() == "Linux":
			def hook():
				readline.insert_text(fp)
				readline.redisplay()
			
			readline.set_pre_input_hook(hook)
			p = input("Target directory: ")
			readline.set_pre_input_hook()
		# Ew.
		else:
			p = input("Target directory: " + os.getcwd() + ("/" if "/" in os.getcwd() else "\\"))

		if len(p.strip()) > 0:
			p = path.join(os.getcwd(), p)
		else:
			p = fp

		os.makedirs(p, exist_ok=True)
		return p
	except KeyboardInterrupt:
		exit()
	except:
		print("This path is not valid! Please try a different one.")
		return get_path()
fp = get_path()

def download_cover():
	try:
		r = requests.get(cover, stream=True)
		
		with open(path.join(fp, "cover.jpg"), "wb") as f:
			shutil.copyfileobj(r.raw, f)
	except KeyboardInterrupt:
		exit()
	except Exception as e:
		print("FAILED TO DOWNLOAD COVER")
		print(e)

clear()
print("Downloading cover...")
download_cover()

first_episode = int(episodes[0][2])
last_episode = int(episodes[-1][2])

clear()
def select_episodes():
	e = argument("--episode") or argument("--episodes")

	try:
		if e is None:
			options = ["Episode " + str(x[2]) for x in episodes]
			selection = pick([f"All {str(len(episodes))} episodes"] + options, " -- PRESS SPACE TO SELECT, ENTER TO CONFIRM -- \nPlease select which episodes you would like to download:", indicator=">>", multiselect=True)

			if selection[0][0].startswith("All") or len(selection) == 0:
				return episodes
			
			return [episodes[x[1] - 1] for x in selection]
		else: # I have no idea what any of this is, I'm too scared to remove it. Good luck.
			range = list(map(lambda n: int(n.strip()) if len(n) > 0 else "all", e or input().split("-")))

			if range[0] == "all":
				return episodes

			if range[0] < first_episode or range[0] > last_episode or (len(range) > 1 and (range[1] < first_episode or range[1] > last_episode or range[1] < range[0])):
				raise

			def find_index(episode):
				for i, ep in enumerate(episodes):
					if int(ep[2]) == episode:
						return i
				return None

			start = find_index(range[0])
			end = find_index(range[1]) if len(range) > 1 else None

			return [episodes[start]] if end is None else episodes[start:end]
	except KeyboardInterrupt:
		exit()
	except Exception as e:
		clear()
		print(e)
		print("Invalid response, please enter a single episode number or a range of episodes within the episode count.")
		input("Press enter to continue...")

		return select_episodes()

clear()
episodes = select_episodes()

for _, id, episode, _ in episodes:
	download_id, _, offical_sources, unofficial_sources, _ = json.loads(requests.get(f"{api}/episode.php?id={id}").content)
	sources = json.loads(unofficial_sources)
	fn = f"Episode {episode}.mp4"

	clear()
	print(f"Preparing to download episode {episode}...")

	def try_download():
		try:
			try:
				source = sources["VidCDN-embed"]
				resolutions = ["1080", "720", "480", "360"]
				re_split = re.search(r"(.+)\/(.+)\.m3u8", source)
				uri_base = re_split[1]
				m3u8_path = re_split[2]

				async def download():
					for resolution in resolutions:
						try:
							m3u8_uri = ".".join(["/".join([uri_base, m3u8_path]), resolution, "m3u8"])

							cmd = f'ffmpeg -i "{m3u8_uri}" -safe 0 -y -async 100 -c copy "{os.path.join(fp, fn)}"'
							process = subprocess.Popen(cmd, shell=True)
							
							if process.wait() == 0:
								return
						except Exception as e:
							print(e)
				asyncio.run(download())
			except Exception as e:
				try:
					source = sources["Direct-directhls"]

					m3u8_To_MP4.multithread_download(source, mp4_file_dir=fp, mp4_file_name=fn)
				except Exception as e:
					source = sources["Mp4upload-embed"].replace("embed-", "")
					mp4_id = re.search(r"mp4upload\.com\/(\S+)\.html", source)[1]

					headers = {
						"authority": "www.mp4upload.com",
						"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
						"accept-language": "en-US,en;q=0.9",
						"cache-control": "max-age=0",
						"dnt": "1",
						"origin": "https://www.mp4upload.com",
						"referer": source,
						"sec-ch-ua": '"Chromium";v="109", "Not_A Brand";v="99"',
						"sec-ch-ua-mobile": "?0",
						"sec-ch-ua-platform": '"Windows"',
						"sec-fetch-dest": "document",
						"sec-fetch-mode": "navigate",
						"sec-fetch-site": "same-origin",
						"sec-fetch-user": "?1",
						"upgrade-insecure-requests": "1",
						"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
					}

					data = {
						"op": "download2",
						"id": mp4_id,
						"rand": "",
						"referer": source,
						"method_free": " ",
						"method_premium": ""
					}
					
					with requests.post(source, verify=False, data=data, headers=headers, stream=True) as r:
						clear()
						print("Direct server download failed, trying alternate server...")

						r.raise_for_status()

						chunk_size = 32768
						total_size = int(r.headers["content-length"])
						downloaded_size = 0
						
						with alive_bar(total_size, title=f"Downloading episode {episode}", ctrl_c=0, unit="B", scale="SI", precision=1) as progress:
							with open(path.join(fp, fn), "wb") as f:
								for chunk in r.iter_content(chunk_size=chunk_size):
									f.write(chunk)

									downloaded_size += chunk_size
									progress(chunk_size)
		except KeyboardInterrupt:
			exit()
		except Exception as e:
			print(e)
			print()
			print("THERE WAS AN ERROR WITH THIS EPISODE | PRESS ENTER TO SKIP EPISODE OR TYPE 'R' AND PRESS ENTER TO RETRY")

			r = input().lower()

			if r == "r":
				try_download()
	try_download()
	
print(f"Done! Successfully downloaded {len(episodes)} episode{'s' if len(episodes) > 1 else ''}!")