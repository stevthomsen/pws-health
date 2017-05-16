#!/usr/bin/env python2.7

import os
import sys
import json
import time
import shutil
import string
import getpass
import argparse
import tempfile
import datetime
import subprocess
import os.path as P

pname = "upload_pthr"
pversion = "1.0.2"
pcontact = "Kevin Tang <ktang@hp.com>; Steven Thomsen <steven.thomsen@hp.com>;"
pdesc = "PWS Trunk Health Test results uploader"

DEBUG = 0

remote="peftech.vcs.rd.hpicorp.net"
remote_dropbox="/pws-health/dropbox"
meta_name="metadata"
test_results_filename="test_results.csv"

def DEBUG_MSG(m):
    if DEBUG:
        print(m)

def get_password():
    os_name = os.name # current 'posix', 'nt', 'mac', 'os2', 'ce', 'java', 'riscos'
    if os_name == 'nt':      # Windows
        return (getpass.win_getpass('linux password: '))
    elif os_name == 'posix': # Linux
        return (getpass.getpass('linux password: '))
    else:                    # Currently don't care about the others
        raise Exception("Only supported on windows and linux")

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

def valid_file(path):
    (valid, p) = path_check_and_absify(path, 'f')
    if not valid:
        raise argparse.ArgumentTypeError("%r is not a valid file." % p)
    return p

def sanitize(s):
    return filter(lambda x: x in string.printable, s) 

def processCol2(label, line):
    place = line.split(',')
    if len(place) >= 2:
        if place[0].strip().lower() == label:
            return place[1]
        else:
            raise Exception("%s: unexpected key '%s'." % (label, place[0]))
    raise Exception("%s: invalid entry '%s'." % (label, line))
    return ""

def JSON_toFile(data, filename):
    fd = None
    try:
        jsondata = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        fd = open(filename, 'w+b')
        fd.write(jsondata)
        fd.close()
        return filename
    except OSError, e:
        if DEBUG: traceback.print_exc()
        print('error: failed to write JSON metadata file \'%s\'.' % filename)
    except Exception, e:
        if DEBUG: traceback.print_exc()
        print('error: failed to write JSON metadata file \'%s\'.' % filename)
    return ""

def create_tar_gz_archive(directory, filename):
    adir = tempfile.mkdtemp()
    tarball_name=P.join(adir, filename + ".tar")
    compressed_name=tarball_name + ".gz"

    tar_cmd=['7z', 'a', '-ttar', tarball_name, P.join(directory, '*')]
    if not subprocess.call(tar_cmd, shell=True):
        gzip_cmd=['7z', 'a', '-tgzip', compressed_name, tarball_name]
        if not subprocess.call(gzip_cmd, shell=True):
            return (adir, compressed_name)
    DEBUG_MSG('error: failed to create \'%s\'.' % P.basename(compressed_name))
    return (adir, "")

def pscp_send(filepath, username, password, remote, remote_path):
    # Use putty scp (pscp) to secure copy to dropBox are
    full_remote='%s@%s:%s' % (username, remote, remote_path)
    # pscp TestResults.tgz remote_user@remote:path_to_dropbox
    pscp_cmd=['pscp',  '-pw', password, filepath, full_remote]
    return False if subprocess.call(pscp_cmd, shell=True) else True

### rmDir :: Path -> Bool #####################################################
def rmDir(d):
    if not os.path.isdir(d):
        print('error: cannot delete \'%s\', path is not a directory, or directory does not exist.' % d)
        return False

    try:
        if DEBUG:
            sys.stdout.write('Deleting \'%s\'...' % d)
            sys.stdout.flush()

        shutil.rmtree(d)

        if DEBUG:
            sys.stdout.write('Done.\n')
            sys.stdout.flush()
    except:
        if DEBUG:
            sys.stdout.write('Failed.\n')
            sys.stdout.flush()
        print('error: exception occurred while deleting \'%s\'.\n' % d)
        return False
    return True

### rmFile :: Path -> Bool #####################################################
def rmFile(p):
    try:
        DEBUG_MSG('Deleting \'%s\'...' % p)
        os.remove(p)
    except OSError, e:
        if e.errno != errno.ENOENT:
            if e.errno == errno.EISDIR:
                DEBUG_MSG('cannot delete \'%s\', it is a directory.' % p)
            elif e.errno == errno.EACCES:
                error(': cannot delete \'%s\'. Access Denied.' % p)
                return False
            elif e.errno == errno.EROFS:
                error(': cannot delete \'%s\'. Read Only Filesystem.' % p)
                return False
            else:
                DEBUG_MSG('exception occurred while deleting \'%s\'. %s\n' % (p, e.strerror))
    return True

def resolve_test_results_filepath(testdir, results_filepath, default_filename=test_results_filename):
    # cases:
    #   A. test_dir = pwd (default)
    #       1. test_results.csv (default)
    #       2. different_name.csv (assuming pwd)
    #       3. path/different_name.csv
    #       4. path/test_result.csv
    #
    #   A.1. = no special processing
    #
    #   A.2. = move to default name
    #          process
    #          move back
    #
    #   A.3./4. = copy with default name
    #             process
    #             delete copied file.
    #
    #   B. test_dir = xyz
    #       1. not provided (default test_results.csv)
    #       2. provided
    #
    #   B.1. = make sure test_results.csv exists
    #
    #   B.2. = copy to test_dir with default name
    #          process
    #          delete from test_dir

    test_results_filepath = P.join(testdir, default_filename)
    if testdir == P.dirname(results_filepath):
        if P.basename(results_filepath) is not default_filename:
            os.rename(results_filepath, test_results_filepath)
            # open file etc
            # remember to undo this later.
    else:
        shutil.copyfile(results_filepath, test_results_filepath)
        # remember to undo this later.
    return test_results_filepath

def main():
    global DEBUG
    # get arg stuff -----------
    # linux_username || prompt
    # test result dir || pwd
    # test results filename || default name
    # remote || default
    # remote path || default
    # Argument handling
    reqp = argparse.ArgumentParser(prog=pname,
                                   formatter_class=argparse.RawTextHelpFormatter,
                                   version='%(prog)s ' + pversion + ' by ' + pcontact,
                                   description=pdesc)

    reqp.add_argument('-vv', '--debug',
                      action='store_true', default=False,
                      help='Print debug messages to stdout.')

    reqp.add_argument('-u','--username', action='store', default=raw_input('linux username: '),
                      help='Linux username - used to access the remote location.\n' +
                           'Note: user is prompted if not provided')

    reqp.add_argument('-p', '--password',
                      action='store', default=get_password(),
                      help='Linux password - used to access the remote location.\n' +
                           'Note: user is prompted if not provided')

    reqp.add_argument('-t', '--testdir',
                      metavar='DIR', action='store', default=os.getcwd(), type=valid_dir,
                      help='Directory containing test results and supporting files. ie: coredumps, logs, etc\n' +
                           'Default: current working directory')

    reqp.add_argument('-r', '--results_csv',
                      metavar="FILE", action='store', default=test_results_filename, type=valid_file,
                      help='Path to test results file - csv file generated from the PWS Trunk Health Test Result Template.')

    reqp.add_argument('-s', '--remote',
                      metavar="HOSTNAME", action='store', default=remote,
                      help='Hostname or IP of the remote.')

    reqp.add_argument('-x', '--remote_path',
                      metavar="PATH", action='store', default=remote_dropbox,
                      help='Path to upload test results on the remote.')

    args = reqp.parse_args()
    argsl = vars(args)
    DEBUG = argsl['debug']

    try:
        results_filepath = resolve_test_results_filepath(argsl['testdir'], argsl['results_csv'])
        f = open(results_filepath, 'r')
    except Exception as e:
        print("cannot open test results file '%s'. reason: %s" % (argsl['results_csv'], str(e)))
        exit(2)

    # First part of file should be like:
    #Test,Pass/Fail,Comments
    #Metadata,,
    #Tester,Phin Yeang,
    #Datetime,"August 9,2016",
    #Product,Limo_mfp unit# B516 (lp3 limo mfp),
    #FirmwareURL,http://peftech.vcd.hp.com/pws-external/UTC_2016-08-09_14_30/limo_lp3/,
    #Test Cases Passed,52,
    #Test Cases Failed,5,
    #Percentage Passed,91.23,
    # As a consequence of using a read-ahead buffer, combining next() with other file methods
    #(like readline()) does not work right.
    #next(f) # skip header: test, pass/fail, comments
    ignore_header = f.readline()
    #next(f) # skip header: metadata
    ignore_header = f.readline()
    tester   = processCol2("tester", sanitize(f.readline()))            # Tester,Phin Yeang,
    testtime = processCol2("datetime", sanitize(f.readline()))          # Datetime,"August 9, 2016",
    product  = processCol2("product", sanitize(f.readline()))           # Product,Limo_mfp unit# B516 (lp3 limo mfp),
    url      = processCol2("firmwareurl", sanitize(f.readline()))       # FirmwareURL,@http://peftech.vcd.hp.com/pws-external/UTC_2016-08-09_14_30/limo_lp3/,
    passed   = processCol2("test cases passed", sanitize(f.readline())) # Test Cases Passed,52,
    failed   = processCol2("test cases failed", sanitize(f.readline())) # Test Cases Failed,5,
    pass_pct = processCol2("percentage passed", sanitize(f.readline())) # Percentage Passed,91.23,
    epoch    = time.time()
    systime  = datetime.datetime.fromtimestamp(epoch).strftime('%Y-%m-%dT%H:%M:%SZ')
    DEBUG_MSG("Tester = " + tester)
    DEBUG_MSG("Test Time = " + testtime)
    DEBUG_MSG("Product = " + product)
    DEBUG_MSG("url = " + url)
    DEBUG_MSG("passed = " + passed)
    DEBUG_MSG("failed = " + failed)
    DEBUG_MSG("Pass percentage = " + pass_pct)
    DEBUG_MSG("epoch = " + str(epoch))
    DEBUG_MSG("Sys Time = " + systime)

    # determine toplevel pass/fail
    try:
        failed_int = int(failed)
    except Exception as e:
        print("Improper failed number '%s' in '%s'. reason: %s"
              % (failed, argsl['results_csv'], str(e)))
        exit(3)

    if failed_int > 0:
        pass_fail = "FAIL"
    else:
        pass_fail = "PASS"

    metadata = { 'system_info' : { 'url'               : url
                                 , 'datetime'          : systime
                                 , 'username'          : argsl['username']
                                 , 'pass_fail'         : pass_fail }
                 
               , 'test_info'   : { 'tester'            : tester
                                 , 'passed'            : passed
                                 , 'failed'            : failed
                                 , 'percentage_passed' : pass_pct
                                 , 'product'           : product
                                 , 'test_time'         : testtime } }
    
    metadata_filepath = JSON_toFile(metadata, P.join(argsl['testdir'], meta_name))
    if not metadata_filepath:
        raise Exception('failed to write metadata to file.')

    (archive_dir, archive_filepath) = create_tar_gz_archive(argsl['testdir'], "%s_%s" % (argsl['username'], epoch))
    if not P.isfile(archive_filepath):
        raise Exception('failed to create tar.gz.')

    if not pscp_send(archive_filepath, argsl['username'], argsl['password'], argsl['remote'], argsl['remote_path']):
        raise Exception("failed to upload test results to '%s'." % argsl['remote'])

    # Clean up
    rmFile(metadata_filepath)
    rmDir(archive_dir)

    return True

if __name__ == '__main__':
    exit(0 if main() else 1)
