import fire
from ratelimit import rate_limited
import requests
import plistlib
import os
import urllib
import pdb
import json
from collections import namedtuple
import time

mobileActionBaseURL = 'https://api.mobileaction.co'
AutocompleteResult = namedtuple('AutocompleteResult', 'search term priority')
ExpandedAutocompleteResult = namedtuple('ExpandedAutocompleteResult', 'search term priority popularity iPhoneRank iPadRank')
MobileActionApp = namedtuple('MobileActionApp', 'appId appName')
alphabet = 'abcdefghijklmnopqrstuvwxyz'

class MobileActionClient(object):
  """A class for communicating with the Mobile Action API"""
  errorHandler = None

  def __init__(self):
    self.apiKey = 'APIKEY'
    self.getFunction = requests.get
    self.limitedTime = None

  def get(self, url):
    if self.limitedTime is not None:
      currentTime = time.time()
      elapsedTime = currentTime - self.limitedTime
      if elapsedTime > 10:
        self.getFunction = requests.get
        self.limitedTime = None
    r = self.getFunction(url)
    if r.status_code != 200:
      if r.status_code == 429 and self.getFunction is requests.get:
        self.getFunction = rate_limited(1)(requests.get)
        self.limitedTime = time.time()
        time.sleep(1)
        return self.get(url)
      if self.errorHandler is not None:
        self.errorHandler('{url}\n{code}\n{text}'.format(url=r.url, code=r.status_code, text=r.text), r)
      return None
    return r


  def getApps(self):
    r = self.get('{base}/apps/?token={key}'.format(base=mobileActionBaseURL, key=self.apiKey))
    if r is None: return []
    data = r.json()['data']
    apps = [MobileActionApp(appId=data[k]['appId'], appName=data[k]['appName']) for k in data]
    return apps

  def getAppDetails(self, trackId):
    url = '{base}/appstore-appinfo/{trackId}/?token={key}'.format(base=mobileActionBaseURL, trackId=trackId, key=self.apiKey)
    r = self.get(url)
    if r is None: return None
    return r.json()

  def getAutocomplete(self, term):
    result = []
    r = self.get('https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?clientApplication=Software&e=true&media=software&term={term}'.format(term=term))
    if r is None: return []

    filename = '{term}.xml'.format(term=term)
    with open(filename, 'wb') as file:
      file.write(r.content)

    with open(filename, 'rb') as file:
      plist = plistlib.readPlist(file)

      for data in plist['hints']:
        autocompleteResult = AutocompleteResult(term, data['term'], data['priority'])
        result.append(autocompleteResult)

      os.remove(filename)
    return result

  def getExpandedAutocomplete(self, term, priorityThreshold, appId=None, letterCallback=None):
    results = []
    for c in alphabet:
      autocompleteTerm = '{term} {c}'.format(term=term, c=c)
      # print('----- {term} -----'.format(term=autocompleteTerm))
      result = self.getAutocomplete(autocompleteTerm)
      filteredResults = [self.expandedAutocompleteResult(r, appId) for r in result if r.priority >= priorityThreshold]
      results += filteredResults
      if letterCallback is not None:
        if not letterCallback(c, filteredResults): break

    # print(results)
    return results

  def getKeywordMetadata(self, term):
    url = '{base}/appstore-keyword-ranking/{countryCode}/keyword-metadata?keyword={keyword}&token={key}'.format(base=mobileActionBaseURL, countryCode='US', keyword=urllib.parse.quote(term), key=self.apiKey)
    r = self.get(url)
    if r is None: return None
    return r.json()

  def expandedAutocompleteResult(self, autocompleteResult, appId):
    keywordMetadata = self.getKeywordMetadata(autocompleteResult.term)
    popularity = None if (keywordMetadata is None or 'popularity' not in keywordMetadata) else keywordMetadata['popularity']
    appRanking = self.getAppRanking(autocompleteResult.term, appId)
    iPadRank = None
    iPhoneRank = None
    if appRanking is not None:
      for item in appRanking:
          if item['appKind'] == 'IPHONE':
              iPhoneRank = item['rank']
          if item['appKind'] == 'IPAD':
              iPadRank = item['rank']
    return ExpandedAutocompleteResult(autocompleteResult.search, autocompleteResult.term, autocompleteResult.priority, popularity, iPhoneRank, iPadRank)

  def getAppRanking(self, term, appId):
    url = '{base}/appstore-keyword-ranking/{trackId}/{countryCode}/{keyword}/keywordrankings?keyword={keyword}&token={key}'.format(base=mobileActionBaseURL, countryCode='US',trackId=appId, keyword=urllib.parse.quote(term), key=self.apiKey)
    r = self.get(url)
    if r is None: return None
    return r.json()

if __name__ == '__main__':
  fire.Fire(MobileActionClient)
