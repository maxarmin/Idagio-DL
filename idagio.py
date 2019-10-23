#Rough beta build.

import os
import re
import sys
import time
import json
import platform
import traceback

import idapy
import requests
from tqdm import tqdm
from mutagen import File
import mutagen.id3 as id3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3NoHeaderError

client = idapy.Client()

def get_os():
	plat = platform.system()
	if plat == 'Windows':
		return True
	else:
		return False

def os_cmds(arg):
	if get_os():
		if arg == "c":
			os.system('cls')
		elif arg == "t":
			os.system('title Idagio-DL R1 (by Sorrow446)')
	else:
		if arg == "c":
			os.system('clear')
		elif arg == "t":
			sys.stdout.write('\x1b]2;Idagio-DL R1 (by Sorrow446)\x07')

def read_config():
	with open("config.json") as f:
		return json.load(f)

def exist_check(f):
	if os.path.isfile(f):
		os.remove(f)
			
def dir_setup(dir):
	if not os.path.isdir(dir):
		os.makedirs(dir)
		# try:
			# os.makedirs(dir)
		# except OSError:
			# pass

def sanitize(f):
	if get_os():
		return re.sub(r'[\\/:*?"><|]', '-', f)
	else:
		return re.sub('/', '-', f)
		
def write_tags(f, meta, cov):
	if f.endswith('.mp3'):
		try: 
			audio = id3.ID3(f)
		except ID3NoHeaderError:
			audio = id3.ID3()
		audio['TRCK'] = id3.TRCK(encoding=3, text=str(meta['TRACK']) + "/" + str(meta['TRACKTOTAL']))
		legend={
			"ALBUM":id3.TALB,
			"ALBUMARTIST":id3.TPE2,
			"ARTIST":id3.TPE1,
			"COPYRIGHT":id3.TCOP,
			"TITLE":id3.TIT2,
			"YEAR":id3.TYER}
		for tag, value in meta.items():
			if not tag in ['UPC', 'TRACK', 'TRACKTOTAL']:
				id3tag = legend[tag]
				audio[id3tag.__name__] = id3tag(encoding=3, text=value)
		with open(cov, 'rb') as cov_obj:
			audio.add(id3.APIC(3, 'image/jpeg', 3, '', cov_obj.read()))
		audio.save(f, 'v2_version=3')
	else:
		audio = FLAC(f)
		for tag, value in meta.items():
			audio[tag] = str(value)
			image = Picture()
		image.type = 3
		image.mime = "image/jpeg"
		with open(cov, 'rb') as cov_obj:
			image.data = cov_obj.read()
			audio.add_picture(image)
		audio.save()

def multi_artists(pre, track):
	post = ""
	for artist in pre:
		if track:
			post += artist['persons'][0]['name'] + ", "
		else:
			post += artist['name'] + ", "
	return post[:-2]
	
def parse_meta(j, meta, num, tot):
	if meta:
		if len(j['workpart']['work']['authors']) > 1:
			artist = multi_artists(j['workpart']['work']['authors'], True)
		else:
			artist = j['workpart']['work']['authors'][0]['persons'][0]['name']
		meta['ARTIST'] = artist
		meta['TITLE'] = j['title']
		meta['TRACK'] = num
		return meta
	else:
		if len(j.participants) > 1:
			artist = multi_artists(j.participants, False)
		else:
			artist = j['participants'][0]['name']
		post_meta={
			'ALBUM':j['title'],
			'ALBUMARTIST':artist,
			'COPYRIGHT':j['copyright'],
			'TRACKTOTAL':tot,
			'YEAR':j['publishDate'].split('-')[0],
			'UPC':j['upc']}
		return post_meta

def download(url, f, num, tot, title, ref, spec):
	print("Downloading track " + num + " of " + tot + ": " + title + spec)
	r = requests.get(url, stream=True, headers={"range":"bytes=0-", "referer":ref,
		'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'})
	r.raise_for_status()
	size = int(r.headers.get('content-length', 0))
	with open(f, 'wb') as f:
		with tqdm(total=size, unit='B',
			unit_scale=True, unit_divisor=1024,
			initial=0, miniters=1) as bar:		
				for chunk in r.iter_content(32*1024):
					if chunk:
						f.write(chunk)
						bar.update(len(chunk))
def download_cov(url, cov):
	r = requests.get(url)
	r.raise_for_status()
	with open (cov, 'wb') as f:
			f.write(r.content)

def main(email, pwd, qual, scheme, label, ext, spec):
	while True:
		os_cmds('c')
		print("Signed in successfully - " + label + " account.\n")
		url = input("Input Idagio web player URL:").strip()
		if not url:
			continue
		elif not url.startswith('https://app.idagio.com/albums/', 0):
			print("Invalid URL.")
			time.sleep(1)
			continue
		os_cmds('c')
		slug = url.split('/')[-1]
		meta = client.get_album_meta(slug)	
		ids = meta['trackIds']
		tot = len(ids)
		album_meta = parse_meta(meta, "", "", tot)
		title = album_meta['ALBUM']
		album_fol = meta['participants'][0]['name'] + " - " + title
		album_fol_s = os.path.join("Idagio-DL downloads", sanitize(album_fol))
		cov = os.path.join(album_fol_s, "cover.jpg")
		dir_setup(album_fol_s)
		exist_check(cov)
		num = 0		
		print(album_fol + "\n")		
		for track, id in zip(meta['tracks'], ids):	
			num += 1
			final_meta = parse_meta(track['piece'], album_meta, num, "")
			title = final_meta['TITLE']
			pre = os.path.join(album_fol_s, str(num) + ext)
			post = os.path.join(album_fol_s, str(num).zfill(2) + scheme + sanitize(title) + ext)	
			exist_check(pre)
			exist_check(post)
			download(client.get_track_url(url, id, qual).url, pre, str(num), str(tot), title, url, spec)
			download_cov(meta.imageUrl, cov)
			write_tags(pre, final_meta, cov)
			try:
				os.rename(pre, post)
			except OSError:
				print("Failed to rename track.")
		

if __name__ == '__main__':
	try:
		os_cmds('t')
		cfg = read_config()
		email = cfg['email']
		pwd = cfg['password']
		qual = cfg['quality']
		scheme = cfg['naming_scheme']
		label = client.auth(email, pwd).user.plan
		if scheme == "1":
			scheme = ". "
		elif scheme == "2":
			scheme = " - "
		if qual == "1":
			qual = "50"
			ext = ".mp3"
			spec = " - 192 kbps MP3"
		if qual == "2":
			qual = "70"
			ext = ".mp3"
			spec = " - 320 kbps MP3"
		if qual == "3":
			qual = "90"
			ext = ".flac"
			spec = " - 16-bit FLAC"
		main(email, pwd, qual, scheme, label, ext, spec)
	except (KeyboardInterrupt, SystemExit):
		sys.exit()
	except:
		traceback.print_exc()
		input("\nAn exception has occurred. Press enter to exit.")
		sys.exit()