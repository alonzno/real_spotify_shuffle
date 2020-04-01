import sys
import re
import os
import json
import time
from random import randrange
from collections import namedtuple

from http.server import HTTPServer, BaseHTTPRequestHandler

import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

import inquirer

'''
	BEGIN Class Declarations
'''
PlaylistInfo = namedtuple('PlaylistInfo',['id','length'])

class OAuthRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		request_path = self.path
		self.server.url = request_path

class OAuthHTTPServer:
	def __init__(self, addr):
		self.server = HTTPServer(addr, OAuthRequestHandler)
		self.server.url = None

'''	
	END Class Declarations
'''

'''
	BEGIN Function Declarations
'''
def prompt_for_user_token_mod(
	username,
	scope=None,
	client_id=None,
	client_secret=None,
	redirect_uri=None,
	cache_path=None,
	oauth_manager=None,
	show_dialog=False
):
	if not oauth_manager:
		if not client_id:
			client_id = os.getenv("SPOTIPY_CLIENT_ID")

		if not client_secret:
			client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

		if not redirect_uri:
			redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

		if not client_id:
			print(
				"""
				You need to set your Spotify API credentials.
				You can do this by setting environment variables like so:
				export SPOTIPY_CLIENT_ID='your-spotify-client-id'
				export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
				export SPOTIPY_REDIRECT_URI='your-app-redirect-url'
				Get your credentials at
					https://developer.spotify.com/my-applications
			"""
			)
			raise spotipy.SpotifyException(550, -1, "no credentials set")

		cache_path = cache_path or ".cache-" + username

	sp_oauth = oauth_manager or spotipy.SpotifyOAuth(
		client_id,
		client_secret,
		redirect_uri,
		scope=scope,
		cache_path=cache_path,
		show_dialog=show_dialog
	)

	# try to get a valid token for this user, from the cache,
	# if not in the cache, the create a new (this will send
	# the user to a web page where they can authorize this app)

	token_info = sp_oauth.get_cached_token()

	if not token_info:

		server_address = ('', 8420)
		httpd = OAuthHTTPServer(server_address)

		import webbrowser

		webbrowser.open(sp_oauth.get_authorize_url())
		httpd.server.handle_request()


		if httpd.server.url:
			url = httpd.server.url

			code = sp_oauth.parse_response_code(url)
			token = sp_oauth.get_access_token(code, as_dict=False)
	else:
		return token_info["access_token"]

	# Auth'ed API request
	if token:
		return token
	else:
		return None

def get_token():
	cred_f = None
	cache_f = None

	try:
		cred_f = open(os.path.dirname(os.path.abspath(__file__)) + '/credentials.json')
		credentials = json.loads(cred_f.read())
		username = credentials['username']
		client_id = credentials['id']
		client_secret = credentials['secret']
		redirect_uri = credentials['redirect']
		scope = 'user-read-currently-playing playlist-modify-public playlist-modify-private'
		cache_path = os.path.dirname(os.path.abspath(__file__)) + '/.cache-alonzoa-us'
		

		try:
			cache_f = open(cache_path)
			data = json.loads(cache_f.read())
			if (data['expires_at'] > int(time.time())):
				return util.prompt_for_user_token(username, 
												  scope, 
												  client_id=client_id, 
												  client_secret=client_secret, 
												  redirect_uri=redirect_uri,
												  cache_path=cache_path)
			else:
				raise IOError
		except IOError:
			#TODO ADD server intercept req
			return prompt_for_user_token_mod(username, 
											 scope, 
											 client_id=client_id, 
											 client_secret=client_secret, 
											 redirect_uri=redirect_uri,
											 cache_path=cache_path)
		finally:
			if cache_f:
				cache_f.close()
	except IOError as e:
		print(e)
		print('It appears you are lacking the credentials.json file.')
		print('No soup for you')
		quit()
	finally:
		if cred_f:
			cred_f.close()


def shuffledIndicesFisherYates(length):
	arr = list(range(length))
	for i in range(length-1):
		j = randrange(i, length)

		temp = arr[i]
		arr[i] = arr[j]
		arr[j] = temp

	return arr

def scatterTracks(spotify, username, playlist_id, targets):
	for i, t in enumerate(targets):
		print(t," to ", i)
		spotify.user_playlist_reorder_tracks(username, playlist_id, t, i)

def selfUpdateFile():
	fin = open(__file__, 'r')
	code = fin.read()
	fin.close()

	prompt = "Enter your Spotify username.\nYou only have to do it once.\nDon't mess it up because you will only get one try.\nThis is self modifying code.\nI know.\nBad looks.\nBut if you mess it up you will have to give me a call.\nOr if you want to look at the source and fix feel free.\n\n"
	print(prompt)
	username = input("Enter you Spotify username: ")
	while len(username) == 0:

		print("Inputed empty string")
		username = input("Enter you Spotify username: ")

	username = username.strip()

	code = code.replace("alonzoa-us", username, 2);

	fout = open(__file__, 'w')
	fout.write(code)
	fout.close

	print("\n\nPlease rerun the program.  You don't have to do that again.  Hopefully")
	quit()
'''
	END Fundtion Declarations
'''

'''
	BEGIN Main Method
'''

#TODO add args
try:
	token = get_token()

	username = "UNASSIGNED"
	if username == "UNASSIGNED":
		selfUpdateFile()

	spotify = spotipy.Spotify(auth=token)

	playlist_data = spotify.user_playlists(username);

	playlists = { x['name']: PlaylistInfo(x['id'],x['tracks']['total']) for x in playlist_data['items']}
	
	questions = [
    inquirer.List(
        "playlist",
        message="What playlist do you want to shuffle?",
        choices=playlists.keys(),
	    ),
	]

	answer = inquirer.prompt(questions)

	playlist_info = playlists[answer['playlist']]

	print(playlist_info.id, playlist_info.length)

	targets = shuffledIndicesFisherYates(playlist_info.length)
	scatterTracks(spotify, username, playlist_info.id, targets)


except Exception as e:
	print(e)
	print("Hey what gives, OAuth Failed")

'''
	END Main Method
'''