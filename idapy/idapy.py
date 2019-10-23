# Rough wrapper for idagio-DL.

import os
import sys
import requests

from idapy.exceptions import AuthenticationError, IneligibleError

# Suppress traceback. Only works on some versions of Python.
sys.tracebacklimit = 0

class Client:
	def __init__(self):
		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'})

	def api_call(self, epoint, **kwargs):
		url = 'https://api.idagio.com/' + epoint
		if epoint == "login.json":
			url = 'https://app.idagio.com/' + epoint
			json={
				'username':kwargs['email'], 
				'password':kwargs['pwd']}
		elif epoint == "v2.0/albums/":
			url += kwargs['slug']
			params = ""
			headers={
				'Referer':'https://app.idagio.com/discover'}
		elif epoint == "v1.8/content/track/":	
			url += str(kwargs['id']) + '?'
			params={
				'quality':kwargs['qual'],
				'format':'2',
				'client_type':'web-test',
				'client_version':'13.23.3',
				'device_id':'web'}
			headers={
				'Authorization':'Bearer ' + self.token,
				'Referer':kwargs['ref']}
		if epoint == "login.json":
			r = self.session.post(url, json=json)
			if r.status_code == 403:
				raise AuthenticationError("Invalid credentials.")
		else:
			r = self.session.get(url, params=params, headers=headers)
		r.raise_for_status()
		return r.json()

	def auth(self, email, pwd):
		j = self.api_call('login.json', email=email, pwd=pwd)
		if not j['user']['premium']:
			raise IneligibleError("Free accounts are not eligible to download tracks.")
		self.token = j['accessToken']
		return ToDot(j)
	
	def get_album_meta(self, slug):
		return ToDot(self.api_call('v2.0/albums/', slug=slug)['result'])
	
	def get_track_url(self, ref, id, qual):
		return ToDot(self.api_call('v1.8/content/track/', ref=ref, id=id, qual=qual))

class ToDot(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for key, value in self.items():
			if type(value) is dict:
				self[key] = ToDot(value)

	def __setitem__(self, key, item):
		if type(item) is dict:
			item = ToDot(item)
		super().__setitem__(key, item)

	__setattr__ = __setitem__
	__getattr__ = dict.__getitem__