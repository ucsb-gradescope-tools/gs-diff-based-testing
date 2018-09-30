#!/usr/bin/env python3

#from __future__ import print_function

import json
import shutil
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
from pprint import pformat
import time
import difflib
from io import StringIO


testSchema ={
  "type": "object",
  "properties": {
    "stdout": {
      "type": "number"
    },
    "stderr": {
      "type": "number"
    },
    "stdin": {
      "type": "string"
    },
    "return": {
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
    },
    "timeout": {
      "type": "number"
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
       if (isinstance(e, JSONDecodeError)):
           retVal["error"]=e.msg
       else:
           retVal["error"]=e.message
   return retVal
    

def loadResultsJsonIfExists(inputfile):
  default_results = { "tests" : [] }

  if inputfile == "":
    return default_results

  try:
    results = json.load(open(inputfile))
  except:
    results = default_results
  return results    

def haltWithError(message):
    print (message)
    sys.exit(1)


def resultFile(outdir,ta,which):
   "generate the filename in which we store result of reference or student test"
   return os.path.join(outdir,  "%05d.%s" % (ta["linenumber"],which))
 
def generate_stdout_and_stderr(args,ta,outdir):
  " generate the files such as 00003.stdout and 00003.stderr for a test on line 3"
  if "test" in ta and "timeout" in ta["test"]:
     timeout = ta["test"]["timeout"]
  else:
     timeout = 5
  if "test" in ta and "stdin" in ta["test"]:
     stdin_string=ta["test"]["stdin"]
  else:
     stdin_string=""
  with open(resultFile(outdir,ta,'stdout'),'w') as out, \
       open(resultFile(outdir,ta,'stderr'),'w') as err, \
       open(resultFile(outdir,ta,'return'),'w') as ret:
    shell_command = ta["shell_command"].strip()
    if args.verbose > 2:
       print("About to call subprocess.call(\""+shell_command+"\")")
       print("ta['test']['stdin']=",ta['test']['stdin'])
    try:      
      p = subprocess.run(shell_command, stdout=out, stderr=err,shell=True,timeout=timeout,input=stdin_string,encoding="utf-8")
      return_code = p.returncode
      ret.write(str(return_code))
      if (args.verbose > 1):
        print("*** return_code=",return_code," *** shell_command=",shell_command)
      return
    except subprocess.TimeoutExpired:
      print("WARNING: ",shell_command," TIMED OUT AFTER",timeout," seconds")
      
      
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
              else:
                 ta["shell_command"]=line
                 testAnnotations.append(ta)
                 
    return testAnnotations

def outputDir(args,isReference):
   if isReference:
     return args.script + "-reference"        
   else:
     return args.script + "-student"

def makeGSTest(ta,stdout_or_stderr):
  result = {}
  if "visibility" in ta["test"]:
    result["visibility"]=ta["test"]["visibility"]
  if "name" in ta["test"]:
    result["name"]=ta["test"]["name"] + " (" + stdout_or_stderr + ")"
  else:
    result["name"]="Checking " + stdout_or_stderr + " from " + ta["shell_command"].strip()
  return result
   
def generateOutput(args,testAnnotations):
   
  " generate the reference or student output by running each command "
  output_dir = outputDir(args,args.reference)
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
      if "test" in ta and "filename" in ta["test"]:
        filename = ta["test"]["filename"]
        if args.verbose > 1:
          print("LOOKING FOR ["+filename+"]")
          if (os.path.isfile(filename)):
            shutil.copy2(filename,output_dir)
          else:
            touch(os.path.join(output_dir,filename+"-MISSING"))

def checkDiffs(args,ta,stdout_or_stderr,gsTests):
  if args.verbose > 2:
    print("checkDiffs for ",stdout_or_stderr)
    pprint(ta)
  if not "test" in ta:
    return
  test = ta["test"]                        
  if stdout_or_stderr in test:
    gsTest = makeGSTest(ta,stdout_or_stderr)
    gsTest["max_score"] = test[stdout_or_stderr] 
    referenceFilename = resultFile(outputDir(args,True),ta,stdout_or_stderr)
    studentFilename = resultFile(outputDir(args,False),ta,stdout_or_stderr)
    performDiff(args,ta,gsTest,gsTests,referenceFilename,studentFilename)            
         
def checkDiffsForFilename(args,ta,gsTests):
  if not "test" in ta:
    return
  test = ta["test"]                        
  if "filename" in test:
    filename = test["filename"]
    gsTest = makeGSTest(ta,"Output file " + filename)
    gsTest["max_score"] = test["points"]
    referenceFilename = os.path.join(outputDir(args,True),filename)
    studentFilename = os.path.join(outputDir(args,False),filename)
    if (not os.path.isfile(referenceFilename)):
      haltWithError("No output for " + filename + " for reference solution")
    if (os.path.isfile(studentFilename + "-MISSING")):
      gsTest["score"]=0
      gsTest["output"]="Missing output in student solution for " + filename
      gsTests.append(gsTest)            
    else:
      performDiff(args,ta,gsTest,gsTests,referenceFilename,studentFilename)


def performDiff(args,ts,gsTest,gsTests,referenceFilename,studentFilename):
  with open(referenceFilename) as f1, open(studentFilename) as f2:

    # Hack to make comparison less picky about final new lines
    lines_from_f1 = list(map(lambda x:x.strip(), f1.readlines()))
    lines_from_f2 = list(map(lambda x:x.strip(), f2.readlines()))
    
    diffs = list(difflib.unified_diff(lines_from_f1,lines_from_f2,
                                      fromfile="expected",tofile="actual"))            
    if (len(diffs)==0):
      gsTest["score"]=gsTest["max_score"]
    else:
      gsTest["score"]=0
      gsTest["output"]="\n".join(diffs)
    gsTests.append(gsTest)  
            
         
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
    parser.add_argument('--inputfile', '-i', default="results.json")
    parser.add_argument('--outputfile', '-o', default="results.json")
    
    args = parser.parse_args()    

    if (not os.path.isfile(args.script)):
        haltWithError("ERROR: the script " + args.script + " does not exist")

    testAnnotations = extractTestAnnotations(args)

    if args.verbose > 2:
       pprint(testAnnotations)

    generateOutput(args,testAnnotations)
    
    if not args.reference:

       reference_dir = outputDir(args,True)
       if (not os.path.isdir(reference_dir)):
         haltWithError("Cannot perform diff; reference output "+reference_dir+" not found")

      
       results = loadResultsJsonIfExists(args.inputfile)

       gsTests = []
       
       for ta in testAnnotations:
          checkDiffs(args,ta,"stdout",gsTests)
          checkDiffs(args,ta,"stderr",gsTests)
          checkDiffs(args,ta,"return",gsTests)          
          checkDiffsForFilename(args,ta,gsTests)
          
       results["tests"] += gsTests
       if "score" in results:
         for t in gsTests:
           results["score"] += t["score"]
                 
       with open(args.outputfile, 'w') as outfile:
          json.dump(results, outfile,indent=2)

       
       

    
