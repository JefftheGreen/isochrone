# /usr/bin/env python
# -*- coding: utf-8 -*-

import googlemaps
from utilities.timeout import timeout
import new_math as math
import configparser
import argparse
from datetime import datetime as dt
from CGAL.CGAL_Kernel import Point_2
from CGAL.CGAL_Alpha_shape_2 import *
import os
import re

config = configparser.ConfigParser()
config.read('config.ini')
CENTERS = config['geography']['centers'].split('\n')[1:]
SN_BOUNDS = [float(l) for l in config['geography']['sn_bounds'].split('\n')[1:]]
EW_BOUNDS = [float(l) for l in config['geography']['ew_bounds'].split('\n')[1:]]
DATA_DIR = config['dirs']['data_dir']
LOG_FILE = os.path.join(os.path.relpath(os.curdir),
                        DATA_DIR, config['dirs']['distances'])
TIMESTAMP = int(config['misc']['timestamp'])
ANALYSES_DIR = config['dirs']['analyses_dir']
DECILE_HEAD = config['dirs']['deciles_head']
DECILE_TAIL = config['dirs']['deciles_tail']
ALPHA_HEAD = config['dirs']['alpha_head']
ALPHA_TAIL = config['dirs']['alpha_tail']
ALPHA_VALUE = config['misc']['alpha']
config.read(config['dirs']['keyfile'])
KEY = config['google']['directions']


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
            if len(lines) == 0:
                with open(self.log, mode='w+') as outfile:
                    outfile.write(self.output_header)
            if not lines[0].strip() == self.output_header.strip():
                print(lines[0])
                print(self.output_header)
                raise ValueError
            point_no = len(lines) - 1
            lng, lat = math.binary_divide_space(EW_BOUNDS, SN_BOUNDS, point_no)
            distances = self.distances(lat, lng)
            self.write(point_no, lat, lng, distances)

def get():
    agent = Agent(KEY, LOG_FILE)
    while True:
        agent.iterate()

def read_decile(n):
    file = ''.join([DECILE_HEAD, str(n), DECILE_TAIL])
    path = os.path.join(os.path.relpath(os.curdir), todays_anal_dir(), file)
    with open(path) as file:
        file.readline()
        points = file.readlines()
        points = [p.split() for p in points]
        return [(float(p[0]), float(p[1])) for p in points]


def get_alpha(n, last_alpha):
    points = read_decile(n)
    points = [Point_2(*n) for n in points]
    alpha = Alpha_shape_2()
    alpha.make_alpha_shape(points)
    alpha.set_alpha(1000)
    return [[(p.x(), p.y())
             for p in (alpha.segment(f).vertex(0),
                       alpha.segment(f).vertex(1))]
            for f in alpha.alpha_shape_edges()]

def to_cycle(alpha):
    points = []
    while len(alpha) > 0:
        if points:
            new_segment = [j for j in alpha if j[1] == last_point][0]
            last_point = new_segment[0]
            alpha.remove(new_segment)
        else:
            last_point = alpha.pop()[0]
        points.append(last_point)
    return points

def todays_anal_dir():
    dir = os.path.join(os.path.relpath(os.curdir), DATA_DIR, ANALYSES_DIR,
                       str(dt.now().date()))
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return dir

def make_alpha(n, last_alpha):
    alpha_cycle = to_cycle(get_alpha(n, last_alpha))
    text = 'lat\tlng'
    for point in alpha_cycle:
        ptext = '\t'.join([str(xy) for xy in point])
        text = '\n'.join([text, ptext])
    fname = ''.join([ALPHA_HEAD, str(n), ALPHA_TAIL])
    fname = os.path.join(todays_anal_dir(), fname)
    with open(fname, 'w+') as file:
        file.write(text)
    return(text)

def make_alphas():
    fnos = []
    for fname in os.listdir(todays_anal_dir()):
        regex = '([0-9]+)'.join([DECILE_HEAD, DECILE_TAIL])
        print(regex)
        match = re.match(regex, fname)
        if match:
            fname = os.path.join(todays_anal_dir(), fname)
            if os.path.isfile(fname):
                fnos.append(int(match.group(1)))
    fnos.sort(reverse=True)
    last_alpha = None
    for fno in fnos:
        last_alpha = make_alpha(fno, last_alpha)
        print(len(last_alpha))

def test():
    make_alphas()

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str)
    args = parser.parse_args()
    if args.command == 'get':
        get()
    elif args.command == 'alphas':
        make_alphas()
    elif args.command == 'test':
        test()

if __name__ == '__main__':
    run()