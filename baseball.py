#!/Users/josephplotkin/anaconda/bin/python
import numpy as np
from scipy import linalg
import baseballsite as bs
from pandas import Series, DataFrame
import pandas as pd
import sys
# some motivation on using scipy here: http://docs.scipy.org/doc/scipy/reference/tutorial/linalg.html

BASE_STATES = [[0,0,0], [1,0,0], [1,1,0], [1,1,1], \
                [0,1,1], [0,0,1], [1,0,1], [0,1,0]]
#need to include third out absorbing state
TOTAL_OUTS = 4

PROB_COLUMNS = ['AB', '1B', '2B', '3B', 'HR', 'OUT']

#default value for scoring from first base on a double
#in the event that per player probs of this are computed
#they must be added to PROB_COLUMNS as 'SF1OD'
SCORE_FROM_1B_ON_DOUBLE = 0.3

#Same as above, add to PROB_COLUMNS as '3BOS'
FIRST_TO_3B_ON_SINGLE = 0.3

def BuildGameStates():
    '''returns tuple (basestate, outs) where basestates
    is a list with three elements'''
    outArray = np.array([[i] * len(BASE_STATES) for i in range(TOTAL_OUTS)]).ravel()
    baseArray = BASE_STATES * TOTAL_OUTS   
    res = []
    #this is disgusting, there has to be a one-liner somehow
    for i in range(len(baseArray)):
        fullState = list(baseArray[i])
        fullState.append(outArray[i])
        res.append(tuple(fullState))   
    return res

def FillState(x, y, Probs):
    res = 0
    #out combinations
    if y[3] == x[3] + 1 and x[:3] == y[:3]:
        res = Probs.OUT
    #home run combinations
    if x[3] == y[3] and y[:3] == (0,0,0):
        res = Probs.HR
    #triple combinations
    if x[3] == y[3] and y[2] == 1 and y[:1] == (0,0):
        res = Probs['3B']
    #double combinations
    if x[3] == y[3] and y[1] == 1 and y[0] == 0:
        #was a runner on first?
        if x[0] == 1:
            if y[2] == 1:
                res = Probs['2B']*(1-Probs.get('SF1OD', SCORE_FROM_1B_ON_DOUBLE))
            else:
                res = Probs['2B']*Probs.get('SF1OD', SCORE_FROM_1B_ON_DOUBLE)
        else:
            #no runner on first so should now be no runner on third
            if y[2] == 0:
                res = Probs['2B']
    #single combinations
    if x[3] == y[3] and y[0] == 1:
        if x[:2] == (0,0) and y[1:3] == (0,0):
            res = Probs['1B']
        if x[:2] == (0,1):
            #does runner on second score?
            if y[2] == 1:
                res = Probs['1B']*Probs.get('SF2OS', SCORE_FROM_2B_ON_SINGLE)
            if y[2] == 0:
                res = Probs['1B']*(1-Probs.get('SF2OS', SCORE_FROM_2B_ON_SINGLE))
        if x[:2] == (1,0):
            #does runner on first move to second?
            if y[1:3] == (0,1):
                res = Probs['1B']*Probs.get('3F1OS', FIRST_TO_3B_ON_SINGLE)
            if y[1:3] == (1,0):
                res = Probs['1B']*(1-Probs.get('3F1OS', FIRST_TO_3B_ON_SINGLE))
        if x[:2] == (1,1):
            #possibilities -> (score, second), (score, third), (second, third)
            #(score, second)
            if y[1:3] == (1,0):
                res = Probs['1B']*Probs.get('SF2OS', SCORE_FROM_2B_ON_SINGLE)*(1-Probs.get('3F1OS', FIRST_TO_3B_ON_SINGLE))
            elif y[1:3] == (0,1):
                res = Probs['1B']*Probs.get('SF2OS', SCORE_FROM_2B_ON_SINGLE)*Probs.get('3F1OS', FIRST_TO_3B_ON_SINGLE)
            elif y[1:3] == (1,1):
                res = Probs['1B']*(1-Probs.get('SF2OS', SCORE_FROM_2B_ON_SINGLE))*(1-Probs.get('3F1OS', FIRST_TO_3B_ON_SINGLE))
    return res

class Team(object):
    def __init__(self, name):
        self.name = name
        self._lineup = None
        site = bs.ESPN()
        self.rawTeamData = site.GetTeam(self.name)
        self.teamProbs = self.ComputeIndividualProbs(self.rawTeamData)
        
    def ComputeIndividualProbs(self, d):
        res = DataFrame([], columns=PROB_COLUMNS, index = d.index)
        denom = d.AB + d.BB
        singles = d.H - (d['2B'] + d['3B'] + d['HR'])
        res['AB'] = d.AB
        res['1B'] = (singles + d.BB) / denom
        res['2B'] = d['2B'] / denom
        res['3B'] = d['3B'] / denom
        res['HR'] = d['HR'] / denom
        res['OUT'] = 1 - (res['1B'] + res['2B'] + res['3B'] + res['HR'])
        self.individualProbs = res
        return res
    
    @property
    def lineup(self):
        return self._lineup

    @lineup.setter
    def lineup(self, value):
        #make sure there are the right number of players
        if len(value) != 9:
            raise ValueError('Lineup must be exactly nine players')
        #make sure the players are actually on the team
        mask = ~np.in1d(value, self.teamProbs.index)
        if np.any(mask):
            notOnTeam = value[mask]
            raise ValueError('Lineup contains players not on team: %s' % notOnTeam)
        self._lineup = self.teamProbs.ix[value]

    @property
    def players(self):
        return self.teamProbs.index

    @players.setter
    def players(self, value):
        raise AttributeError('Cannot set team players')

    def TransitionMatrix(self, player):
        gameStates = BuildGameStates()
        sz = len(gameStates)
        transitionMatrix = DataFrame(0, columns = gameStates, index = gameStates)
        playerProbs = self.individualProbs.ix[player]
        for c in transitionMatrix.columns:
            for r in transitionMatrix.index:
                try:
                    transitionMatrix[r][c] = FillState(r, c, playerProbs)
                except:
                    print '[!!] %s -> %s' % (r,c)
                    exit(-1)
        return transitionMatrix

    def ExpectedOneInningRuns(self):
        pass

if __name__ == '__main__':
    team = sys.argv[1]
    team = Team(team)
    players = team.players
    lineup = players[:9]
    team.lineup = np.array(lineup)
    print team.lineup
    states = BuildGameStates()
    for s in states:
        print s
    print '[!!] len(states) %s' % len(states)
    transMat = team.TransitionMatrix('Chris Hatcher')
    print transMat
