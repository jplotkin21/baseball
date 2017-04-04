#!/usr/bin/env python

import urllib2
import json
from retries import *
from bs4 import BeautifulSoup
import re
from pandas import DataFrame, Series
import pandas as pd

SITE_CONFIG = { 
    'ESPN':
    {
    'url': 'http://espn.go.com/mlb/team/stats/batting/_/name/%s'
    },
    'XMLStats':
    {'url': 'https://erikberg.com/mlb/',
     'Headers': {'User-Agent': '/robots/contact(jplotkin21@gmail.com)'}
    }
            }

class BaseballSite(object):
    def __init__(self, sitename):
        self.config = SITE_CONFIG[sitename]
    
    def __Connect(self, url):
        headers = self.config.get('Headers')
        req = urllib2.Request(url, None)
        rawHTML = urllib2.urlopen(req).read()
        return rawHTML
    
    def Connect(self, url):
        return self.__Connect(url)

    def __GetURL(self):
        return self.config['url']
    
    def GetURL(self):
        return self.__GetURL()

class ESPN(BaseballSite):
    def __init__(self):
        super(ESPN, self).__init__('ESPN')
        
    def GetTeam(self, team):
        res = []
        url = self.GetURL() % team
        rawHTML = self.Connect(url)
        soup = BeautifulSoup(rawHTML, 'html.parser')
        table = soup.find('table', {'class': 'tablehead'})
        headers = [rec.text for rec in table.find('tr', {'class': 'colhead'})]
        playerStats = table.find_all('tr', {'class': re.compile("player") })
        for row in playerStats:
            values = []
            for d in row.find_all('td'):
                val = d.text
                val = val.encode('ascii','ignore')
                if val.replace('.','').isdigit():
                    val = float(val)
                values.append(val)
            res.append(dict(zip(headers, values)))
        res = DataFrame(res)
        res = res.set_index('NAME')
        return res
    
class XMLStats(BaseballSite):
    def __init__(self):
        super(self)
        
    def GetAllTeams(self):
        url = '%s/teams.json' % self.config['url']
        html = self.Connect(url)
        res = json.loads(html.decode('UTF-8'))
        return res
    
    
if __name__ == '__main__':
    site = ESPN()
    team = site.GetTeam('lad')
    print team
    site = XMLStats()
    teams = site.GetAllTeams()
    for r in teams:
        print '[!!] team_id: %s' % r['team_id']
