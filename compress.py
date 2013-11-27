#!/usr/bin/env python3

import argparse
import os.path
import os
import re
import tempfile
import shutil
import subprocess

from collections import defaultdict
from multiprocessing import Process
from datetime import datetime

WIDTH=640
HEIGHT=480

filename_re = re.compile(r'^image(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{2}).jpg$')

def group_files_by_date(path):
    d = defaultdict(list)
    for f in os.listdir(path):
        m = filename_re.match(f)
        if m:
            date = "20{}-{}-{}".format(m.group(1), m.group(2), m.group(3))
            d[date].append(os.path.join(path, f))
    return d

def handle_camera(camera, args):
    in_path  = os.path.join(args.input_dir, camera)
    out_path = os.path.join(args.output_dir, camera)

    processes = {}
    for date, files in group_files_by_date(in_path).items():
        if datetime.strptime(date, '%Y-%m-%d').date() == datetime.today().date():
            continue
        processes[date] = Process(target=handle_date, args=(out_path, date, files, args.fps, camera))
        processes[date].start()

    for p in processes.values():
        p.join()

def handle_date(out_path, date, files, fps, camera):
    tmp = tempfile.NamedTemporaryFile(prefix='kantine-surveillance_', suffix='.txt', mode='w+')

    for f in sorted(files):
        tmp.write(f + "\n")

    args = ( 'mencoder'
           , 'mf://@{}'.format(tmp.name)
           , '-mf', 'w={}:h={}:fps={}:type=jpg'.format(WIDTH, HEIGHT, fps)
           , '-ovc', 'lavc'
           , '-lavcopts', 'vcodec=mpeg4'
           , '-oac', 'copy'
           , '-of', 'avi'
           , '-o', os.path.join(out_path, '{}.avi'.format(date))
           , '-really-quiet'
           )

    subprocess.check_output(args)

    for f in files:
        os.unlink(f)

if __name__ == '__main__':
    def check_dir(d):
        if not os.path.exists(d):
            raise argparse.ArgumentTypeError("'{}' does not exist".format(d))
        return os.path.abspath(d)

    parser = argparse.ArgumentParser(description="Convert surveillance photos to a movie clip")
    parser.add_argument('-f', '--fps', help='frames per second', type=int, default=5, metavar='N')
    parser.add_argument('-i', '--input-dir', help='input directory', default='.', metavar='DIR', type=check_dir)
    parser.add_argument('-o', '--output-dir', help='output directory', default='.', metavar='DIR', type=check_dir)
    parser.add_argument('cameras', metavar='C', nargs='+',
                        help='a camera corresponding to a directory in the input/output directories')
    args = parser.parse_args()

    processes = {}
    for c in args.cameras:
        processes[c] = Process(target=handle_camera, args=(c, args))
        processes[c].start()

    for p in processes.values():
        p.join()
