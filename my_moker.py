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
        print('delete ' + str(image))
    else:
        print('This is not image')


def rm(container):
    netns_name = 'netns_' + str(container)
    if container[0: 2] == "ps":
        NetNS(netns_name).close()
        netns.remove(netns_name)
        btrfsutil.delete_subvolume(btrfs_path + '/' + str(container))
        print('delete ' + str(container))

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
    for image in os.listdir(btrfs_path):
        if image[0:4] == 'img_':
            file = open(btrfs_path + '/' + image + '/img.source', 'r')
            print(image, file.read())
            file.close()


def ps():
    for ps in os.listdir(btrfs_path):
        if image_file[0:4] == 'img_':
            file = open(btrfs_path + '/' + ps + '/' + ps + '/.cmd', 'r')
            print(ps, file.read())
            file.close()


def run(uuid1, *args):
    id = uuid.uuid4()
    uuid_name = 'ps_' + str(id.fields[5])[:4]

    mac = str(id.fields[5])[:2]
    if mocker_check(uuid1) == 1:
        print('No image named ' + str(uuid1))
        return
    if mocker_check(uuid_name) == 0:
        print(uuid_name)
        print('UUID conflict, retrying...')
        return
    cmd = args
    ip_last_octet = 103

    with IPDB() as ipdb:
        veth0_name = 'veth0_' + str(uuid_name)
        veth1_name = 'veth1_' + str(uuid_name)
        netns_name = 'netns_' + str(uuid_name)
        bridge_if_name = 'bridge0'

        existing_interfaces = ipdb.interfaces.keys()

        with ipdb.create(kind='veth', ifname=veth0_name, peer=veth1_name) as i1:
            i1.up()
            if bridge_if_name not in existing_interfaces:
                ipdb.create(kind='bridge', ifname=bridge_if_name).commit()
            i1.set_target('master', bridge_if_name)

        netns.create(netns_name)

        with ipdb.interfaces[veth1_name] as veth1:
            veth1.net_ns_fd = netns_name

        ns = IPDB(nl=NetNS(netns_name))
        with ns.interfaces.lo as lo:
            lo.up()
        with ns.interfaces[veth1_name] as veth1:
            veth1.address = "02:42:ac:11:00:{0}".format(mac)
            veth1.add_ip('10.0.0.{0}/24'.format(ip_last_octet))
            veth1.up()
        ns.routes.add({'dst': 'default', 'gateway': '10.0.0.1'}).commit()

    btrfsutil.create_snapshot(btrfs_path + '/' + uuid1, btrfs_path + '/' + uuid_name)
    file_log = open(btrfs_path + '/' + uuid_name + '/' + uuid_name + '.log', 'w')
    file = open(btrfs_path + '/' + uuid_name + '/' + uuid_name + '.cmd', 'w')
    file.write(str(cmd))
    file.close()
    cg = Cgroup(uuid_name)
    cg.set_cpu_limit(50)
    cg.set_memory_limit(500)

    def in_cgroup():
        try:
            pid = os.getpid()
            cg = Cgroup(uuid_name)

            netns.setns(netns_name)
            cg.add(pid)

        except Exception as e:
            traceback.print_exc()
            file_log.write("Failed to preexecute function")
            file_log.write(e)

    cmd = list(args)
    file_log.write('Running ' + cmd[0] + '\n')
    cwd1 = str(btrfs_path+'/' + uuid_name)
    process = subprocess.Popen(cmd, preexec_fn=in_cgroup, shell=True, cwd=cwd1)
    process.wait()
    file_log.write('Error ')
    file_log.write(str(process.stderr) + '\n')
    file_log.write('Final\n')
    file_log.write('done\n')
    print('Creating', uuid_name)


def exec(uuid_name, *args):
    netns_name = 'netns_' + str(uuid_name)
    cmd = args

    file_log = open(btrfs_path + '/' + uuid_name + '/' + uuid_name + '.log', 'a')
    file = open(btrfs_path + '/' + uuid_name + '/' + uuid_name + '.cmd', 'w')
    file.write(str(cmd))
    file.close()
    cg = Cgroup(uuid_name)
    cg.set_cpu_limit(50)
    cg.set_memory_limit(500)

    def in_cgroup():
        try:
            pid = os.getpid()
            cg = Cgroup(uuid_name)

            netns.setns(netns_name)
            cg.add(pid)

        except Exception as e:
            traceback.print_exc()
            file_log.write("Failed to preexecute function")
            file_log.write(e)

    cmd = list(args)
    file_log.write('Running ' + cmd[0] + '\n')
    cwd1 = str(btrfs_path+'/' + uuid_name)
    process = subprocess.Popen(cmd, preexec_fn=in_cgroup, shell=True, cwd=cwd1)
    process.wait()
    file_log.write('Error ')
    file_log.write(str(process.stderr) + '\n')
    file_log.write('Final\n')
    file_log.write('done\n')


def logs(ps):
    file_log = open(btrfs_path + '/' + ps + '/' + ps + '.log', 'r')
    print(ps)
    print(file_log.read())


def commits(i1, i2):
    if mocker_check(i2) == 1:
        rmi(i2)
    btrfsutil.create_snapshot(btrfs_path + '/' + str(i1), btrfs_path + '/' + str(i2))
    print('Created ' + str(i2))


def help():
    print('Назначение и использование команд:', '\n')
    print('init <directory> - создать образ контейнера используя указанную директорию как корневую. ')
    print('pull <image> - скачать последний тег указанного образа с Docker Hub в образ контейнера.')
    print('rmi <image_id> - удаляет образ c названием <image_id> из локального хранилища.')
    print('images - выводит список локальный образов')
    print('ps - выводит список контейнеров')
    print('run <image_id> <command> - создает контейнер из указанного image_id и запускает его с указанной командой')
    print('exec <container_id> <command> - запускает указанную команду внутри уже запущенного указанного контейнера')
    print('logs <container_id> - выводит логи указанного контейнера')
    print('rm <container_id> - удаляет контейнер с названием <container_id>')
    print('commit <container_id> <image_id> - создает новый образ, применяя изменения из образа container_id к образу image_id')
    print('help - выводит help по командам')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init(sys.argv[2])

        if sys.argv[1] == "pull":
            pull(sys.argv[2])

        if sys.argv[1] == "rmi":
            rmi(sys.argv[2])

        if sys.argv[1] == "rm":
            rm(sys.argv[2])

        if sys.argv[1] == "images":
            images()

        if sys.argv[1] == "ps":
            ps()

        if sys.argv[1] == "run":
            run(sys.argv[2], sys.argv[3])

        if sys.argv[1] == "exec":
            exec (sys.argv[2], sys.argv[3])

        if sys.argv[1] == "logs":
            logs(sys.argv[2])

        if sys.argv[1] == "commits":
            commits(sys.argv[2], sys.argv[3])

        if sys.argv[1] == "help":
            help()
