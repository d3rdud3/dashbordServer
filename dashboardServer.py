import tweepy
import feedparser
from flask import Flask
from flask_cors import CORS, cross_origin
from flask import send_file
from threading import Thread
from flask_socketio import SocketIO, send, emit
from flask import Response
import json
import configparser
import requests
import os

app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)
config = configparser.ConfigParser()
config.read('config.ini')
CORS(app)

# JSON Model object for transport
class JSONRSSEntry(object):
    def __init__(self,title,description,published):
        self.title = title
        self.description = description
        self.published = published

# provide feed data
@app.route("/rss/iphoneblog")
def iphoneblogFeed():
    return prepareRSSResponse(config['feedURLs']['iphoneblogFeedPath'])

@app.route("/rss/heise")
def heiseFeed():
    return prepareRSSResponse(config['feedURLs']['heiseFeedPath'])

@app.route("/rss/jaxenter")
def jaxFeed():
    return prepareRSSResponse(config['feedURLs']['jaxenterfeed'])

@app.route("/rss/welt")
def weltFeed():
    return prepareRSSResponse(config['feedURLs']['weltfeedpath'])

# prepare the plain rss feed response with parsing
def prepareRSSResponse(url):
    preparedValues = prepareEntriesForJSONTransport(url)
    if preparedValues is None:
        resp = Response(
            response="",
            status=500,
            mimetype="application/json")
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    else:
        resp = Response(response=json.dumps(preparedValues, default=obj_dict),
                        status=200,
                        mimetype="application/json")
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

# prepare json objects for RSS feed
def prepareEntriesForJSONTransport(url):
    d = feedparser.parse(url)

    entries = []
    for num in range(1, 5):
        entries.append(JSONRSSEntry(d.entries[num].title,d.entries[num].description,d.entries[num].published))
    return entries

def obj_dict(obj):
    return obj.__dict__

# Server State endpoints
@app.route("/serverstatus/ledRemoteServerAlive")
def remoteServerAlive():
    return pingServer(config['localServerUrls']['ipLEDRemoteServer'])

@app.route("/serverstatus/kodiServerAlive")
def kodiServerAlive():
    return pingServer(config['localServerUrls']['ipKodiServer'])

@app.route("/serverstatus/buildpiServerAlive")
def buildpiServerAlive():
    return pingServer(config['localServerUrls']['ipBuildpiServer'])

@app.route("/serverstatus/ledBackendAlive")
def remoteBackendAlive():
    return callURL(config['localServerUrls']['ledRemoteBackendURL'])

@app.route("/serverstatus/alexaSkillExternalCall")
def remoteExternalBackendAlive():
    return callURL(config['localServerUrls']['externalLEDRemoteURL'])

def pingServer(ip):
    response = os.system("ping -c 1 " + ip)
    if response == 0:
        return 'up'
    else:
        return 'down'

def callURL(url):
    try:
        r = requests.get(url)
        if (r.status_code == requests.codes.ok):
            return 'up'
        else:
            return 'down'
    except:
        return "down"

#Tech feed endpoint
@app.route("/techFeeds")
def hello():
    return "Hello World!"

#-- fond images
@app.route('/fondImage/total')
def totalImage():
    return send_file(config['fondImages']['totalValueImagePath'])

@app.route('/fondImage/tech')
def techImage():
    return send_file(config['fondImages']['techFondValueImagePath'])

@app.route('/fondImage/global')
def globalImage():
    return send_file(config['fondImages']['globalFondValueImagePath'])

@app.route('/fondImage/growth')
def growthImage():
    return send_file(config['fondImages']['growthFondValueImagePath'])


# -- Twitter live websocket service ----
@socketio.on('firstEvent')
def handle_message(message):
#   print('received message: ' + message)
    emit('my response', 'testfromapp')

@socketio.on('myEvent')
def handle_message_event(message):
    print('received message on socket: ' + message)

# stream listener which emits a websocket message
class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        socketio.emit('my response', status._json)
#       print(status.text)

# consume the twitter stream API and emit a message via Websocket
def handletweets():

    auth = tweepy.OAuthHandler(config['twitterAuth']['consumerKey'], config['twitterAuth']['consumerSecret'])
    auth.set_access_token(config['twitterAuth']['accessToken'], config['twitterAuth']['accessTokenSecret'])
    api = tweepy.API(auth)
    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)
    myStream.userstream()
    #myStream.filter(track=['python'])

background_thread = Thread(target=handletweets, args=())
background_thread.start()

if __name__ == '__main__':
    socketio.run(app)

