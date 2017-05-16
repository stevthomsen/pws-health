#!/usr/bin/env python2.7

#
# This script will use inotify to be notified when something is dropped
# (IN_CREATE) into the specified drop place
# (drop_place = "/users/thomsen/temp").  It will wait for the item to be
# finished written to (IN_CLOSE_WRITE) to begin processing.  First it will
# check if the item is a compressed tarball (r:gz mode).  Next it will check
# if there is a member named metadata (meta_name = "metadata").  It will make a
# temporary directory to extract to.  The file metadata is extracted and
# checked for proper components (url, username, datetime and pass_fail).
# the metadata file is removed.  Next we check if results file 
# (results_name = "Test_Results.csv") exists in the tarball.  If we got here
# we have a valid test results tarball.  Make the apporpriate results
# directory (test_results_PASS if test passed or test_results_FAIL).  It
# then will make dirs for the path to extract (so we can later copy cp -r)
# temporary place (dir/test_results_{PASS,FAIL}/username_epoch).  Then extract
# all parts of tarball (additional data maybe presen, so get it too).  Now
# copy to final place (final_place = "/users/thomsen/temp2") and then clean
# up (rmtree of temporary directory and remove tarball)
# 

import os
import json
import time
import errno
import pprint
import shutil
import socket
import string
import tarfile
import argparse
import datetime
import tempfile
import traceback
#import subprocess
import os.path as P
import dateutil.parser as DP # not included in stdlib
from libs.pyinotify import pyinotify

DEBUG = 0
TRASH = 0
LINUX_HOST = True

# create new one per version roll. 'from uuid import uuid4; uuid4().hex'
V_UUID = '605204bb42bf4a4eb8d63c0f46a0f7a7'

pname = "process_pthr"
pversion = "1.0.2"
pcontact = "Kevin Tang <ktang@hp.com>; Steven Thomsen <steven.thomsen@hp.com>;"
pdesc = "PWS Trunk Health Test results processor"

drop_place = "/pws-health/dropbox"
final_place = "/pws-health/external"
trash_can = "/pws-health/dropbox-trashcan"
results_name = "test_results.csv"
meta_name = "metadata"
test_result_base = "test_results_"
PASS = 'PASS'
FAIL = 'FAIL'

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE

# idea from http://blog.eduardofleury.com/archives/2007/09/13
def singleton(name):
    global lock
    lock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        # absract socket - LINUX ONLY
        lock.bind('\0' + name)
    except socket.error:
        return False
    return True

def DEBUG_MSG(m):
    if DEBUG:
        print(m)

def path_check_and_absify(path, _type):
    abspath = P.abspath(path)
    if _type is 'd' and not P.isdir(abspath):
        return (False, '')

    if _type is 'f' and not P.isfile(abspath):
        return (False, '')

    return (True, abspath)

def valid_dir(path):
    (valid, p) = path_check_and_absify(path, 'd')
    if not valid:
        raise argparse.ArgumentTypeError("%r is not a valid directory." % p)
    return p

def delete(path):
    try:
        print("deleting trash: '%s'" % path)
        if P.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except Exception, e:
        if DEBUG: traceback.print_exc()
        print('error: failed to delete trash \'%s\'.\nreason: \'%s\''
              % (path, str(e)))
        return False
    return True

def trash(path):
    DEBUG_MSG("trash called with " + path)
    if TRASH:
        print("trashcan enabled: move '%s' to the trash for triage" % path)
        shutil.move(path, trash_can)
    else:
        delete(path)

def convert_line_endings_to(temp, mode):
        #modes:  0 - Unix, 1 - Mac, 2 - DOS
        if mode == 0:
                temp = string.replace(temp, '\r\n', '\n')
                temp = string.replace(temp, '\r', '\n')
        elif mode == 1:
                temp = string.replace(temp, '\r\n', '\r')
                temp = string.replace(temp, '\n', '\r')
        elif mode == 2:
                import re
                temp = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", temp)
        return temp

def JSON_fromFile(path):
    try:
        DEBUG_MSG('Attempting to open %s ...' % path)
        fd = open(path, 'r')
        temp = fd.read()
        DEBUG_MSG('Contents of \'%s\':\n%s' % (path, temp))
        fd.close()
        jsond = json.loads(temp)
        return jsond
    except Exception, e:
        if DEBUG: traceback.print_exc()
        print('error: could not load \'%s\'. Invalid JSON?' % str(path))
    return {}

def parse_build_dir(s):
    tailpos = s.rfind('UTC_')
    if tailpos >= 0:
        return s[tailpos:-1]
    return ''

def process_metadata(metapath):
    DEBUG_MSG("process_metadata.metapath: \'%s\'" % metapath)
    metad = JSON_fromFile(metapath)
    if DEBUG:
        print("process_metadata: got\n")
        pprint.pprint(metad)
    if metad.get('system_info'):
        if ( metad['system_info'].get('url')        and
             metad['system_info'].get('pass_fail')  and
             metad['system_info'].get('username')   and
             metad['system_info'].get('datetime')   and
             parse_build_dir(metad['system_info']['url']) and
             metad['system_info']['pass_fail'] in [PASS, FAIL] ):

            metad['system_info']['datetime'] = (DP.parse(metad['system_info']['datetime'])).strftime('%s')
            metad['system_info']['build_dir'] = parse_build_dir(metad['system_info']['url'])
            return metad['system_info']
        else:
            if not metad['system_info'].get('url') :
                print('metadata is missing required information: \'url\'.')
            elif not parse_build_dir(metad['system_info']['url']) :
                print('metadata bad information: url: \'%s\'' % metad['system_info']['url'])
            if not metad['system_info'].get('pass_fail'):
                print('metadata is missing required information: \'pass_fail\'.')
            elif not (metad['system_info']['pass_fail'] in [PASS, FAIL]):
                print('metadata is bad information: pass_fail: \'%s\'' % metad['system_info']['pass_fail'])
            if not metad['system_info'].get('username'):
                print('metadata is missing required information: \'username\'.')
            if not metad['system_info'].get('datetime'):
                print('metadata is missing required information: \'datetime\'.')
    else:
        print('metadata is missing required information section: \'system_info\'.')
    return {}

def process_tarball(src_path, dest_path='', f=[]):
    if DEBUG:
        print("process_tarball.src_path: '%s'" % src_path)
        print("process_tarball.dest_path: '%s'" % (dest_path if dest_path else 'to be created as tempdir'))
        print("process_tarball.f: [%s]" % ', '.join(f))

    temp_created = False
    try:
        tarball = tarfile.open(src_path, "r:gz")
        if not dest_path:
            dest_path = tempfile.mkdtemp()
            DEBUG_MSG("process_tarball.dest_path: '%s'" % dest_path)
            temp_created = True
        if not f or len(f) <= 0:
            DEBUG_MSG("process_tarball.f is empty, extracting all files.")
            tarball.extractall(dest_path)
        else:
            for member in f:
                DEBUG_MSG("process_tarball: extract member '%s'" % member)
                tarball.extract(member, dest_path)
    except Exception, e:
        print('error: \'%s\'' % str(e))
        trash(src_path)
        if temp_created:
            delete(dest_path)
            return ''

    return dest_path

# Process dropbox-ed test results tar.gz files.
#
#   open tar.gz file for reading.
#   check that file "metadata" exists in the tar table.
#   make tempdir
#   extract metadata file to tempdir - this is for validating the drop.
#   sanitize metadata of \r\n -> \n
#   grab metadata members (url, pass_fail, username, timestamp)
#   delete metadata file from tempdir -> maybe save for the end or something?
#   check that test_results exist in the tar.gz
#   make directories.
#   extract all the things
#   copy to final resting place.
#   cleanup tempdir/workingdir.
def process(path):
    global meta_name
    global test_result_base

    DEBUG_MSG("process.path: '%s'" % path)
    temp_dirpath = process_tarball(path, f=[meta_name])
    DEBUG_MSG("process.temp_dirpath: '%s'" % temp_dirpath)
    meta4 = process_metadata(P.join(temp_dirpath, meta_name))

    if not meta4:
        print("Invalid meta data")
        delete(temp_dirpath)
        return False

    results_dir = test_result_base + meta4['pass_fail']
    DEBUG_MSG("process.results_dir: '%s'" % results_dir)
    DEBUG_MSG("process: metadata is useless now - we could delete now if we wanted.")
    # remember to delete tempdir_dirpath later.

    # look for test_results.csv
    user_dirname = meta4['username'] + '_' + meta4['datetime']
    temp_report_dirpath = P.join(temp_dirpath, results_dir)
    temp_report_userdir = P.join(temp_report_dirpath, user_dirname)

    try:
        DEBUG_MSG("process: makedirs: '%s'" % temp_report_userdir)
        os.makedirs(temp_report_userdir)
    except OSError, exc:
        if exc.errno == errno.EEXIST and P.isdir(path):
            pass
        else:
            raise
    except Exception, e:
        print("error: failed to create workspace directories: '%s'.\nreason: %s"
              % (temp_report_userdir, str(e)))
        delete(temp_dirpath)
        return False

    process_tarball(path, f=[results_name], dest_path=temp_report_userdir)
    process_tarball(path, dest_path=temp_report_userdir)
    final_dir = P.join(final_place, meta4['build_dir'], results_dir)

    DEBUG_MSG("process: moving '%s/*' -> '%s/.'" % (temp_report_dirpath, final_dir))
    try:
        if P.isdir(final_dir): # final_dir already exists, so need temp_report_dirpath/*
            DEBUG_MSG("process: final_dir '%s' already exists." % final_dir)
            below = os.listdir(temp_report_dirpath)
            for file_or_dir in below:
                DEBUG_MSG("process: moving '%s'/'%s'." % (temp_report_dirpath, file_or_dir))
                shutil.move(P.join(temp_report_dirpath, file_or_dir), final_dir)
        else: # final_dir does not exist, so just move
            DEBUG_MSG("process: final_dir '%s' does not exist." % final_dir)
            shutil.move(temp_report_dirpath, final_dir)

        #if os.path.isfile(final_dir):
        #    delete(final_dir)
        #elif os.path.islink(final_dir):
        #    delete(final_dir)
        #if not os.path.isdir(final_dir):
        #    os.makedirs(final_dir)
        #cp_cmd = "cp -R " + temp_report_dirpath + " " + final_dir

        #DEBUG_MSG("process: cp_cmd =  " + cp_cmd)
        #subprocess.check_call(cp_cmd, shell=True)


    except Exception, e:
        print("error: failed to move test data directory '%s' to gallery" % temp_report_dirpath)
        print("'%s'.\nreason: %s" % (final_dir, str(e)))
        return False

    print("processing done, cleaning up workspace '%s'" % temp_dirpath)
    #delete(temp_dirpath)

    return True

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print("created: '%s'" % event.pathname)

    def process_IN_DELETE(self, event):
        print("deleted: '%s'" % event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        print("write closed: '%s'" % event.pathname)
        if P.isfile(event.pathname) and event.pathname.endswith('.tar.gz'):
            process(event.pathname)
        trash(event.pathname)

def main():
    global drop_place
    global final_place
    global trash_can
    global results_name
    global meta_name
    global test_result_base
    global DEBUG
    global TRASH

    reqp = argparse.ArgumentParser(prog=pname,
                                   formatter_class=argparse.RawTextHelpFormatter,
                                   version='%(prog)s ' + pversion + ' by ' + pcontact,
                                   description=pdesc)

    reqp.add_argument('-vv', '--debug',
                      action='store_true', default=False,
                      help='Print debug messages to stdout.')

    reqp.add_argument('-g', '--trashcan',
                      action='store_true', default=False,
                      help='Enable the trashcan for Oscar.')

    reqp.add_argument('-l','--listendir', metavar="DIR",
                      action='store', default=None, type=valid_dir,
                      help='Directory to watch for drops.')

    reqp.add_argument('-o', '--gallerydir', metavar="DIR",
                      action='store', default=None, type=valid_dir,
                      help='Parent directory to move test results directory to.')

    reqp.add_argument('-t', '--trashdir',
                      metavar='DIR', action='store', default=None, type=valid_dir,
                      help='Where Oscar The Grouch lives and where malformed drops are placed.' +
                           'Note: implies \'--trashcan\'')

    reqp.add_argument('-r', '--results_name',
                      metavar="STRING", action='store', default=results_name,
                      help='Name of the test results file - csv file generated from the PWS Trunk Health Test Recipe Template.')

    reqp.add_argument('-m', '--meta_name',
                      metavar="STRING", action='store', default=meta_name,
                      help='Internal metadata filename.')

    reqp.add_argument('-p', '--result_prefix',
                      metavar="STRING", action='store', default=test_result_base,
                      help='Prefix of test results directory to create.')

    args = reqp.parse_args()
    argsl = vars(args)
    DEBUG = argsl['debug']
    TRASH = argsl['trashcan']
    results_name = argsl['results_name']
    meta_name = argsl['meta_name']
    test_result_base = argsl['result_prefix']

    # must be valid dir to use default in parse args
    if argsl['listendir']:
        drop_place = argsl['listendir']

    if argsl['gallerydir']:
        final_place = argsl['gallerydir']

    if argsl['trashdir']:
        trash_can = argsl['trashdir']
        TRASH = True

    DEBUG_MSG("drop_place: '%s'" % drop_place)
    DEBUG_MSG("final_place: '%s'" % final_place)
    DEBUG_MSG("trash_can: '%s'" % trash_can)
    DEBUG_MSG("results_name: '%s'" % results_name)
    DEBUG_MSG("meta_name: '%s'" % meta_name)
    DEBUG_MSG("test_result_base: '%s'" % test_result_base)
    DEBUG_MSG("DEBUG: '%s'" % str(DEBUG))
    DEBUG_MSG("TRASH: '%s'" % str(TRASH))

    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(drop_place, mask, rec=True)

    notifier.loop()

if __name__ == '__main__':
    if LINUX_HOST and not singleton(V_UUID):
        print('init: could not aquire lock.')
        exit(10)
    print('init: lock aquired.')
    exit(0 if main() else 1)

