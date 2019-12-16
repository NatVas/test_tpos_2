#!/usr/bin/env python3
import os
import random
from cgroups import Cgroup
from pyroute2 import IPDB, NetNS, netns
import sys
import btrfsutil
import subprocess
import traceback
import requests
import json
import tarfile
import uuid


btrfs_path = '/home/vagrant/mocker'

list_of_img = []


def mocker_check(image):
    it = btrfsutil.SubvolumeIterator(btrfs_path, info=True, post_order=True)
    try:
        for path, info in it:
            if str(path) == image:
                return 0
        return 1
    except Exception as e:
        print(e)
    finally:
        it.close()

def rmi(image):
    if image[0: 3] == "img":
        btrfsutil.delete_subvolume(btrfs_path + '/' + str(image))
        print('Removed ' + str(image))
    else:
        print('This is not container')

def init(directory):
    image = 'img_' + str(random.randint(100, 155))
    if os.path.exists(directory):
        if mocker_check(image) == 0:
            mocker_init(directory)
            return
        btrfsutil.create_subvolume(btrfs_path + '/' + str(image))
        os.system('sudo cp -rf --reflink=auto ' + directory + '/* ' + btrfs_path + '/' + str(image))
        if not os.path.exists(btrfs_path + '/' + str(image) + '/img.source'):
            file = open(btrfs_path + '/' + str(image) + '/img.source', 'w')
            file.write(directory)
            file.close()
        print("created " + str(image))
    else:
        print("Noo directory named " + directory + " exists")
      

def pull():
    pass


def images():
    pass


def ps():
    pass


def run():
    pass


def exec():
    pass


def logs():
    pass


def commits():
    pass


def help():
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init(sys.argv[2])

        if sys.argv[1] == "pull":
            pull()

        if sys.argv[1] == "rmi":
            rmi(sys.argv[2])

        if sys.argv[1] == "images":
            images()

        if sys.argv[1] == "ps":
            ps()

        if sys.argv[1] == "run":
            run()

        if sys.argv[1] == "exec":
            exec ()

        if sys.argv[1] == "logs":
            logs()

        if sys.argv[1] == "commits":
            commits()

        if sys.argv[1] == "help":
            help()
