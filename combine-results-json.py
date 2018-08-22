#!/usr/bin/env python3

from __future__ import print_function

import json
import shutil
import argparse
import textwrap
import os
import sys


fallback_message = textwrap.dedent('''\
****************************************************
There may be a problem with your submission
that the autograder system wasn't anticipating, 
so there is no way to give a helpful error message.

There also may be a problem with autograder itself
Please consult your TA or instructor for assistance, 
and show them this error message.

****************************************************
''')
                                   
                                   
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=\
                                     'Combine separate Gradescope results.json files into one',
                                     formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument('jsonfiles', nargs='+',
                        help= textwrap.dedent('''\
                        multiple results.json files, e.g. results1.json results2.json etc.
                        
                        These might come from different phases, e.g. from a diff-based testing phase
                        followed by a junit phase, followed by another diff-based testing phase.
                        '''))

    parser.add_argument('--outputfile', '-o',  default="results.json")
    parser.add_argument('--verbose', '-v', action='count', default=0)
    
    args = parser.parse_args()    

    results = {"tests":[]}
    results_objects = []

    for infile_name in args.jsonfiles:
      if (not os.path.isfile(infile_name)):
        haltWithError("ERROR: the inputfile " + infile_name + " does not exist")
      with open(infile_name,'r') as infile:
        try:
            contents = json.load(infile)
        except:            
            the_test = {"name": "TEST HARNESS ERROR",
                        "max_score": 1,
                        "score": 0  ,
                        "output": fallback_message + "Problem file: " + infile_name}
            contents = {"tests" : [ the_test ] }
                        
        results_objects.append(contents)

    for ro in results_objects:
        if "tests" in ro and type(ro["tests"])==list:
          results["tests"] += ro["tests"]
        
    with open(args.outputfile, 'w') as outfile:
      json.dump(results, outfile,indent=2)

    
