import asyncio
import json
import os
import re
import shutil
import sys
from os import path, system

import m3u8_To_MP4
import pyppeteer
import requests
from alive_progress import alive_bar
from pyppeteer_stealth import stealth

clear = lambda: system("cls" if sys.platform == "win32" else "clear")

def argument(arg, default = None):
	if arg in sys.argv:
		return sys.argv[sys.argv.index(arg) + 1]
	return default

api = "https://animension.to/public-api"

clear()
if not "--name" in sys.argv:
	print("Search anime:")
name = argument("--name") or input()

clear()
dub = "--dub" in sys.argv
sub = "--sub" in sys.argv

if not dub and not sub:
	print("Sub or Dub? (Press enter to skip filtering)")
	r = input()

	if "sub" in r.lower():
		sub = True
	elif "dub" in r.lower():
		dub = True

filtering = ""
if sub:
	filtering = "&dub=0"
elif dub:
	filtering = "&dub=1"

clear()
results = json.loads(requests.get(f"{api}/search.php?search_text={name}&page=1&sort=az{filtering}").content)

def select_anime():
	try:
		idx = 1
		for name, id, cover_uri, is_sub in results:
			print(f"{idx}) {name}")

			idx += 1
		
		print()
		print("Select anime:")
		idx = int(input())

		if idx < 1 or idx > len(results):
			raise
		return results[idx - 1]
	except:
		clear()

		print("Invalid response, please enter a selection number from below.")
		print()

		return select_anime()
	
anime, id, cover, _ = select_anime()
episodes = json.loads(requests.get(f"{api}/episodes.php?id={id}").content)[::-1]
fp = path.join(os.getcwd(), anime)

os.makedirs(fp, exist_ok=True)

def download_cover():
	try:
		r = requests.get(cover, stream=True)
		
		with open(path.join(fp, "cover.jpg"), "wb") as f:
			shutil.copyfileobj(r.raw, f)
	except Exception as e:
		print("FAILED TO DOWNLOAD COVER")
		print(e)

clear()
print("Downloading cover...")
download_cover()

clear()
def select_episodes():
	e = argument("--episode") or argument("--episodes")

	if e is None:
		print(f"Which episodes would you like to download? (1-{len(episodes)})")
		print(f"Examples: 1 OR 3-5 OR 1-12 OR press enter to download all.")

	try:
		range = list(map(lambda n: int(n.strip()) if len(n) > 0 else "all", e or input().split("-")))

		if range[0] == "all":
			return episodes

		if range[0] < 1 or range[0] > len(episodes) or (len(range) > 1 and (range[1] < 1 or range[1] > len(episodes) or range[1] < range[0])):
			raise

		return [episodes[range[0] - 1]] if len(range) == 1 else episodes[range[0] - 1:range[1]]
	except:
		clear()
		print("Invalid response, please enter a single episode number or a range of episodes within the episode count.")
		print()

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
				source = sources["Doodstream-embed"].replace("/e/", "/d/")

				async def download():
					browser = await pyppeteer.launch()
					print("launched")
					page = await browser.newPage()
					print("page created")
					await stealth(page)
					print("stealth enabled")

					await page.goto(source)
					print("page loaded")
					await page.waitForSelector(".container .download-content > a")
					href = await page.Jeval(".container .download-content > a", "e => e.href")

					await page.goto(href)
					await page.waitForSelector("a.btn.btn-primary")
					download_link = re.search(r"window\.open\(\'(https.+)\', \'_self\'\)", await page.Jeval("a.btn.btn-primary", "e => e.getAttribute('onclick')"))[1]

					headers = {
						"Connection": "keep-alive",
						"Upgrade-Insecure-Requests": "1",
						"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3542.0 Safari/537.36",
						"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
						"Referer": href,
						"Accept-Language": "en-US,en;q=0.9"
					}
					
					with requests.get(download_link, headers=headers, stream=True) as r:
						clear()
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
					await browser.close()

				asyncio.run(download())
			except Exception as e:
				print(e)
				input()
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
		except Exception as e:
			print(e)
			print()
			print("THERE WAS AN ERROR WITH THIS EPISODE | PRESS ENTER TO SKIP EPISODE OR TYPE 'R' AND PRESS ENTER TO RETRY")

			r = input().lower()

			if r == "r":
				try_download()
	try_download()
	
print(f"Done! Successfully downloaded {len(episodes)} episode{'s' if len(episodes) > 1 else ''}!")