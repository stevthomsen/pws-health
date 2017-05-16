#!/usr/bin/env python2.7

import datetime
import string
import time
import os
import subprocess
import getpass
import sys

meta_name="metadata"
fileName="Test_results.csv"

myTime = time.time()

username = raw_input('linux username: ')
remote_password = getpass.win_getpass('linux password: ')

try:
    f = open(fileName, 'r')
except:
    print "Cannot open test results file" + fileName
    quit()

# First part of file should be like:
#Test,Pass/Fail,Comments
#Metadata,,
#Tester,Phin Yeang,
#Datetime,"August 9, 2016",
#Product,Limo_mfp unit# B516 (lp3 limo mfp),
#FirmwareURL,@http://peftech.vcd.hp.com/pws-external/UTC_2016-08-09_14_30/limo_lp3/,
#Test Cases Passed,52,
#Test Cases Failed,5,
#Percentage Passed,91.23,
myLine =f.readline() #Test,Pass/Fail,Comments
myLine =f.readline() #Metadata,,
myLine =f.readline() #Tester,Phin Yeang,
myLine =f.readline() #Datetime,"August 9, 2016",
myLine =f.readline() #Product,Limo_mfp unit# B516 (lp3 limo mfp),
myLine =f.readline() #FirmwareURL,@http://peftech.vcd.hp.com/pws-external/UTC_2016-08-09_14_30/limo_lp3/,
firmwareURL = myLine.replace('FirmwareURL,', '')
chopLine = filter(lambda x: x in string.printable, firmwareURL)
url = chopLine.replace(',', '')

myLine =f.readline() #Test Cases Passed,52,
myLine =f.readline() #Test Cases Failed,5,
if -1 == myLine.find(',0,'): # not found in myLine
    pass_fail = "FAIL"
else:
    pass_fail = "PASS"

myDate = datetime.datetime.fromtimestamp(myTime).strftime('%Y-%m-%dT%H:%M:%SZ')
newFile = open(meta_name, 'w')
newFile.truncate()
newFile.write("url=" + url) # line has \r\n at end
newFile.write("datetime=" + myDate + "\r\n")
newFile.write(username + "\r\n")
newFile.write("pass_fail=" + pass_fail + "\r\n")
# not necessary as f.close() calls f.flush()
#newFile.flush() # double check if necessary.
newFile.close()

# Archive data using 7Zip
# tarball/compressed name chanage to be username_mytime
tarball_name=username + "_" + str(myTime) + ".tar"
compressed_name=username + "_" + str(myTime) + ".tar.gz"
tar_cmd=['7z', 'a', '-ttar', tarball_name, '*']
tar_result = subprocess.check_output(tar_cmd, shell=True)
gzip_cmd=['7z', 'a', '-tgzip', compressed_name, tarball_name]
gzip_result = subprocess.check_output(gzip_cmd, shell=True)

# Use putty scp (pscp) to secure copy to dropBox are
remote="15.98.81.50"
path_to_dropbox="/users/thomsen/temp"
full_remote=username + '@' + remote + ':' + path_to_dropbox
# pscp TestResults.tgz remote_user@remote:path_to_dropbox
pscp_cmd=['pscp',  '-pw', remote_password, compressed_name, full_remote]
pscp_result = subprocess.check_output(pscp_cmd, shell=True)

# Clean up
os.unlink(meta_name)
os.unlink(tarball_name)
os.unlink(compressed_name)
