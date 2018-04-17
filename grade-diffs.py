#!/usr/bin/env python3

from __future__ import print_function

import json
import shutil
import pprint
import argparse
import textwrap
import subprocess
import os
import sys
import re
from jsonschema import validate
from jsonschema import ValidationError
from json.decoder import JSONDecodeError
from pprint import pprint
import time

testSchema ={
  "type": "object",
  "properties": {
    "stdout": {
      "type": "number"
    },
    "stderr": {
      "type": "number"
    },
    "filename": {
      "type": "string"
    },
    "points": {
      "type": "number"
    },
     "name": {
      "type": "string"
    },
    "visibility": {
      "type": "string",
      "enum": [
        "hidden",
        "after_due_date",
        "after_published",
        "visible"
      ]
    }
  },
  "additionalProperties": False
}


def touch(path):
  "from https://stackoverflow.com/questions/12654772/create-empty-file-using-python"
  with open(path, 'a'):
    os.utime(path, None)
    

def lineToTestAnnotation(args,line,linenumber):
   """
    returns a dictionary indicating whether this line is a test annotation or not

    { isTest: bool, True if this is a test annotation with valid json
      test: dict, the json string converted to a dictionary
      isError: bool, True if this appears to be a test annotation attempt with an error in it
      jsonString: str, the json string extracted (or what we got as the json string)
      line: str, the entire line contents,
      linenumber: int, the line number in the file
      error: str, the best error message we can give
    }
   """

   retVal = { "line" : line, "linenumber" : linenumber }

   test_regular_expression="^#[ ]*@test(.*)$" # test it at https://pythex.org/
   
   matches = re.match(test_regular_expression, line.strip())
   if not matches:
       retVal["isTest"]=False
       retVal["isError"]=False       
       return retVal

   retVal["jsonString"]=matches.group(1)

    
   try:
       retVal["test"]=json.loads(retVal["jsonString"])
       v=validate(retVal["test"], testSchema)
       retVal["isTest"]=True
       retVal["isError"]=False
   except (ValidationError, JSONDecodeError) as e:
       retVal["isTest"]=False       
       retVal["isError"]=True
       retVal["error"]=e.msg
   return retVal
    

def loadResultsJsonIfExists():    
    try:
        results = json.load(open('results.json'))
    except:
        results = { "tests" : [] }
    return results    

def haltWithError(message):
    print (message)
    sys.exit(1)


def resultFile(outdir,ta,which):
   "generate the filename in which we store result of reference or student test"
   return os.path.join(outdir,  "%05d.%s" % (ta["linenumber"],which))
 
def generate_stdout_and_stderr(args,ta,outdir):
  " generate the files such as 00003.stdout and 00003.stderr for a test on line 3"
  with open(resultFile(outdir,ta,'stdout'),'w') as out, \
       open(resultFile(outdir,ta,'stderr'),'w') as err:
    output = subprocess.call(ta["shell_command"].strip().split(" "), stdout=out, stderr=err)

    
def processLine(args,line, linenumber):
    if (args.verbose > 1):
        print("linenumber: ",linenumber," line: ",line.strip())
    testAnnotation = lineToTestAnnotation(args,line,linenumber)
    return testAnnotation


def extractTestAnnotations(args):
    " extract list of test annotations from args.script file"
    testAnnotations=[]
    with open(args.script) as infile:
        linenumber = 0
        prevLineWasTestAnnotation = False
        for line in infile:
            linenumber += 1
            if prevLineWasTestAnnotation:
               ta["shell_command"]=line
               testAnnotations.append(ta)
               prevLineWasTestAnnotation = False
            else:
              ta = processLine(args,line,linenumber)
              if ta["isError"]:
                 print("Error on line",linenumber," of ", args.script, " : ",ta["error"])
              if ta["isTest"]:
                 prevLineWasTestAnnotation = True
    return testAnnotations

def outputDir(args):
   if args.reference:
     return args.script + "-reference"        
   else:
     return args.script + "-student"
  
def generateOutput(args,testAnnotations):
   
  " generate the reference or student output by running each command "
  output_dir = outputDir(args)
  if (os.path.isdir(output_dir)):
     print("Removing old directory: ",output_dir)
     try:
        shutil.rmtree(output_dir)
     except Exception:
        haltWithError("Error: was unable to remove " + output_dir)
        
  print("Creating directory ",output_dir,"...")
  try:
    os.mkdir(output_dir)
  except Exception:
    haltWithError("Error: was unable to create " + output_dir)
      
  for ta in testAnnotations:
    generate_stdout_and_stderr(args,ta,output_dir)
    if "filename" in ta["test"]:
       filename = ta["test"]["filename"]
       if args.verbose > 1:
         print("LOOKING FOR ["+filename+"]")
       if (os.path.isfile(filename)):
         shutil.copy2(filename,output_dir)
       else:
         touch(os.path.join(output_dir,filename+"-MISSING"))
                 
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate Gradescope compatible results.json for diff-based testing',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('script', 
        help= textwrap.dedent('''\
        name of script file, e.g. diffs.sh

        The directory diffs.sh-reference should already exist, having been
        populated with the command generate-reference-output.py diffs.sh

        blank lines and lines with \# in first column will be ignored
        other lines will have comments with four comma separated fields, e.g.

          echo foo \# 10, You should echo foo to stdout
          >&2 echo "error" # , , 10, You should echo bar to stderr
        
       '''))

    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--reference', '-r',action='store_true')
    
    args = parser.parse_args()    

    if (not os.path.isfile(args.script)):
        haltWithError("ERROR: the script " + args.script + " does not exist")

    testAnnotations = extractTestAnnotations(args)

    if args.verbose > 2:
       pprint(testAnnotations)

    generateOutput(args,testAnnotations)
    
    if not args.reference:
       
       results = loadResultsJsonIfExists()

       # THIS IS THE PLACE IN THE CODE WHERE YOU ADD TESTS into the results["tests"] array.
       # THIS IS WHERE WE WILL NEED TO DO THE DIFFS.

       for ta in testAnnotations:
          if args.verbose > 0:
             pprint(ta)
          pass
       
       with open('results.json', 'w') as outfile:
          json.dump(results, outfile)

       
       

    
