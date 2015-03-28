#  Title: networkInfo.py
#
#   Abstract: This script is written for part of the STOQS Modernization routine. It
#                 will determine the vagrants Network address and install that information
#                 and other lines to the pg_hba.conf file.
#  Author: Jeremy Gutierrez
#  Email: jergutierrez@csumb.edu
#
#  Date: 03/27/2015
#

import os
import sys

def collectInfo(): #Gather the network information
    os.system("netstat -r >> netInfo.txt") # create and send info to netInfo.txt file

def getNetId(address): # get the network address and return it as a string
    with open('netInfo.txt') as f:
        ip = []
        content = f.readlines()[2:]
        result = [c for c in content[0]] # a list comprehension
        for element in result: # Seperate the ip Address
            if (element == "*"): # Keep only the first IP Address
                break
            else:
               ip.append(element)
        sentence = ip
        sent_str = ""
        for i in sentence: # combine the address into a string
            sent_str += str(i) + ""
            sent_str = sent_str[:-1]
        f.close()
        os.remove('netInfo.txt') # remove the created file
        return sent_str

def createLines(addressString):
    newLine = "host   all    all   "+addressString
    modLine = newLine + "   trust"
    return modLine

def addLines(NLines):
    addA = str(NLines)
    addB = "host    all             all             127.0.0.1/32            trust"
    file = open ('/var/lib/pgsql/9.3/data/pg_hba.conf', 'a')
    file.write(addA)
    file.write("\n")
    file.write(addB)
    file.close()

def main():
    address="" #Setsup the address string
    ipAddress = []
    collectInfo() #Collect the system Information
    addressString = getNetId(address) # This will create a string out of the network address
    NLines = createLines(addressString) # This will create the needed lines for the file
    addLines(NLines) # This will add the needed lines to the file

main()

