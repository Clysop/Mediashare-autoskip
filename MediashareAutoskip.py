import asyncio
import os
import configparser
from dotenv import dotenv_values
import requests
from twitchAPI import twitch, oauth
import SendInput

ENV = dotenv_values()

CONFIG_PATH = 'MediashareAutoskip.ini'

# twitch app credentials
APP_ID = ENV['APP_ID']
APP_SECRET = ENV['APP_SECRET']
USER_SCOPE = [twitch.AuthScope.USER_WRITE_CHAT]

# load stored tokens from config file
config = configparser.ConfigParser()
config.read(CONFIG_PATH)
if ('tokens' not in config):
  config.add_section('tokens')


# returns streamelements api url at given endpoint with channel id
def url(endpoint: str, id=None):
  base_url = 'https://api.streamelements.com/kappa/v2/'

  if (endpoint.count(':channel')):
    if (not id):
      raise TypeError("id parameter not given")

    return base_url + endpoint.replace(':channel', id)

  return base_url + endpoint


# returns true if there's a video playing in mediashare
# the 'player' api endpoint is broken, so a workaround is done instead:
# if the currently playing video is the same as the latest video in history, playback is stopped
def get_playing_state(id, headers):
  r = requests.get(url('songrequest/:channel/playing', id),
                   headers=headers).json()

  current_song = None
  if ('_id' in r):
    current_song = r['_id']

  r = requests.get(url('songrequest/:channel/history', id),
                   {'limit': 1}, headers=headers).json()

  return not (len(r['history']) and r['history'][0]['song']['_id'] == current_song)


# callback function for twitch user_auth_refresh_callback
async def update_twitch_tokens(token: str, refresh_token: str):
  config['tokens']['twitch_token'] = token
  config['tokens']['twitch_refresh_token'] = refresh_token
  with open(CONFIG_PATH, 'w') as f:
    config.write(f)


# main loop for asyncio, which is needed by the twitchAPI module
async def main(id):
  # streamelements api headers
  headers = {
      'Authorization': 'Bearer ' + config['tokens']['jwt_token'],
      'Accept': 'application/json; charset=utf-8'
  }

  print("\nConnecting to Twitch")
  twitch_session = await twitch.Twitch(APP_ID, APP_SECRET)

  try:
    # authenticate twitch API with tokens from config file, or generate new tokens if needed
    try:
      token = config.get('tokens', 'twitch_token')
      refresh_token = config.get('tokens', 'twitch_refresh_token')

      await twitch_session.set_user_authentication(token, USER_SCOPE, refresh_token)
    except:
      authenticator = oauth.UserAuthenticator(twitch_session, USER_SCOPE)
      token, refresh_token = await authenticator.authenticate()

      await twitch_session.set_user_authentication(token, USER_SCOPE, refresh_token)
      await update_twitch_tokens(token, refresh_token)

    twitch_session.user_auth_refresh_callback = update_twitch_tokens

    user_info = await oauth.get_user_info(twitch_session.get_user_auth_token())

    print("Connected to chatroom:", user_info['preferred_username'])
    await twitch_session.send_chat_message(user_info['sub'], user_info['sub'],
                                           'Mediashare autoskip connected to chat')

    is_playing = get_playing_state(id, headers)
    print("Video is playing" if is_playing else "No video playing")

    while True:
      if (is_playing):
        # check if currently playing video has stopped
        if (not get_playing_state(id, headers)):
          is_playing = False
          print("No video playing")
          await asyncio.sleep(1)
          # send play/pause command to the os
          SendInput.SendKey(SendInput.VK_MEDIA_PLAY_PAUSE)

      else:
        # check if there's a new video in queue ready to be played.
        r = requests.get(
            url('songrequest/:channel/next', id), headers=headers).json()

        if (r['song']):
          print("Video in queue")
          # use twitch api to send '!skip' commands in chat since streamelements api doesn't support skipping
          await twitch_session.send_chat_message(user_info['sub'], user_info['sub'], '!skip')
          print("Skip message sent")
          is_playing = True
          # send play/pause command to the os
          SendInput.SendKey(SendInput.VK_MEDIA_PLAY_PAUSE)

      await asyncio.sleep(3)

  finally:
    await twitch_session.close()


try:
  # get streamelements JWT token from config, or ask user if it's missing
  while True:
    if (not config.get('tokens', 'jwt_token', fallback='')):
      config['tokens']['jwt_token'] = input(
          "Please enter your JWT token from StreamElements: ")

    # test streamelements API with JWT token
    r = requests.get(url('channels/me'), headers={
        'Authorization': 'Bearer ' + config['tokens']['jwt_token'],
        'Accept': 'application/json; charset=utf-8'
    })

    if r.status_code == 200:
      id = r.json()['_id']
      print("\nConnected to StreamElements API")
      print("User ID:", id)
      break
    else:
      print("\nConnection to StreamElements API failed")
      data = r.json()
      print("Error: {}\nMessage: {}\n".format(
          data['error'], data['message']))
      config['tokens']['jwt_token'] = ''

  with open(CONFIG_PATH, 'w') as f:
    config.write(f)

  asyncio.run(main(id))

except KeyboardInterrupt:
  None
