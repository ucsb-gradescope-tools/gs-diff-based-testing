#!/usr/bin/env python3

from __future__ import print_function

import json
import shutil
import argparse
import textwrap
import os
import sys


         
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Combine separate Gradescope results.json files into one',
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

    for infile in args.jsonfiles:
      if (not os.path.isfile(infile)):
        haltWithError("ERROR: the inputfile " + infile + " does not exist")        
      with open(infile,'r') as infile:
        results_objects.append(json.load(infile))

    for ro in results_objects:
        if "tests" in ro and type(ro["tests"])==list:
          results["tests"] += ro["tests"]
        
    with open(args.outputfile, 'w') as outfile:
      json.dump(results, outfile,indent=2)

       
       

    
