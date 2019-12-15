import sys
import requests
import os
import json
import tarfile
import btrfsutil

list_of_dir = []


def init(directory):
    btrfs_util_create_subvolume(directory, 0, NULL, NULL);
    list_of_dir.append(directory)
    return len(list_of_dir-1)

def pull():
    pass


def rmi(id_directory):
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
            exec()

        if sys.argv[1] == "logs":
            logs()

        if sys.argv[1] == "commits":
            commits()

        if sys.argv[1] == "help":
            help()




