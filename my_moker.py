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

def auth(library, image):
    token_req = requests.get(
        'https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s/%s:pull'
        % (library, image))
    return token_req.json()['token']


def get_manifest(image, tag, registry_base, library, headers):
    print("Fetching manifest for %s:%s..." % (image, tag))

    manifest = requests.get('%s/%s/%s/manifests/%s' %
                            (registry_base, library, image, tag),
                            headers=headers)
    print(manifest)
    return manifest.json()
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
      

def pull(image):
    registry_base = 'https://registry-1.docker.io/v2'
    library = 'library'
    headers = {'Authorization': 'Bearer %s' % auth(library, image)}
    manifest = get_manifest(image, 'latest', registry_base, library, headers)

    image_name_friendly = manifest['name'].replace('/', '_')
    print(image_name_friendly)
    with open(os.path.join(btrfs_path, image_name_friendly + '.json'), 'w') as cache:
        cache.write(json.dumps(manifest))

    dl_path = os.path.join(btrfs_path, image_name_friendly, 'layers')
    if not os.path.exists(dl_path):
        os.makedirs(dl_path)

    layer_sigs = [layer['blobSum'] for layer in manifest['fsLayers']]
    unique_layer_sigs = set(layer_sigs)

    contents_path = os.path.join(dl_path, 'contents')
    if not os.path.exists(contents_path):
        os.makedirs(contents_path)

    for sig in unique_layer_sigs:
        url = '%s/%s/%s/blobs/%s' % (registry_base, library,
                                     image, sig)
        local_filename = os.path.join(dl_path, sig) + '.tar'

        r = requests.get(url, stream=True, headers=headers)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        with tarfile.open(local_filename, 'r') as tar:
            tar.extractall(str(contents_path))
    init(dl_path)

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
            pull(sys.argv[2])

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
