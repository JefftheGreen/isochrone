# /usr/bin/env python
# -*- coding: utf-8 -*-

import googlemaps
from utilities.timeout import timeout
import new_math as math
import configparser

parser = configparser.ConfigParser()
parser.read('keys.cnf')
KEY = parser['google']['directions']
CENTERS = ['Salem, OR', 'Portland, OR', 'Eugene, OR']
SN_BOUNDS = [42, 46.291719]
EW_BOUNDS = [-116.463761, -124.565233]
LOG_FILE = 'distances.log'
TIMESTAMP = 1514764800  # Jan 1 2018, 0:00:00


class Agent:

    def __init__(self, key, log):
        self.log = log
        self.client = googlemaps.Client(key)

    @property
    def output_header(self):
        before = ['point', 'lat', 'lng']
        after = ['min', 'max', 'sum']
        header = '\t'.join(before + list(CENTERS) + after)
        return header

    def distances(self, lng, lat):
        with timeout(seconds=10):
            routes = [self.client.directions([lng, lat], c,
                                             departure_time=TIMESTAMP)
                      for c in CENTERS]
            legs = [r[0]['legs'] if len(r) else False for r in routes]
            durations = [l[0]['duration']['value'] if l
                         else False for l in legs]
        return durations

    def write(self, point_no, lat, lng, distances):
        if not len(distances) == len(CENTERS):
            raise ValueError
        with open(self.log, mode='a') as outfile:
            dist_strs = [str(d) for d in distances + [min(distances),
                                                      max(distances),
                                                      sum(distances)]]
            line = '\t'.join([str(n) for n in (point_no, lat, lng)]
                             + list(dist_strs))
            outfile.write('\n')
            outfile.write(line)

    def iterate(self):
        with open(self.log, mode='r') as infile:
            lines = infile.readlines()
            if not lines[0].strip() == self.output_header.strip():
                print(lines[0])
                print(self.output_header)
                raise ValueError
            point_no = len(lines) - 1
            lng, lat = math.binary_divide_space(EW_BOUNDS, SN_BOUNDS, point_no)
            distances = self.distances(lat, lng)
            self.write(point_no, lat, lng, distances)



def run():
    agent = Agent(KEY, LOG_FILE)
    while True:
        agent.iterate()

if __name__ == '__main__':
    run()