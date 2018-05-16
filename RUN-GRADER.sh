#!/bin/sh

# YOU SHOULD NOT NEED TO EDIT THIS FILE

if [ "$#" -eq 1 ]; then
    SUBMISSION_SOURCE=`pwd`/$1
else
    SUBMISSION_SOURCE=/autograder/submission
fi

if [ -d $SUBMISSION_SOURCE ]; then  
   echo "Checking submission from $SUBMISSION_SOURCE"
else
   echo "ERROR: $SUBMISSION_SOURCE does not exist"
   exit
fi

copy_files_from_dir_if_it_exists () {
    if [ -d $1 ]; then
        cp -v $1/* .
    fi
}

/bin/rm -rf MAKE-STUDENT-OUTPUT
mkdir -p MAKE-STUDENT-OUTPUT

cd MAKE-STUDENT-OUTPUT

copy_files_from_dir_if_it_exists ../EXECUTION-FILES
copy_files_from_dir_if_it_exists ../BUILD-FILES

for f in $EXPECTED_FILES; do
    if [ -f $SUBMISSION_SOURCE/$f ]; then
        cp -v $SUBMISSION_SOURCE/$f .
    else
        echo "WARNING: Expected file $f not found in $SUBMISSION_SOURCE"
    fi
done

make clean
make $MAKE_TARGET

rm -f results.json
../${DIFF_TOOLS}/grade-diffs.py ../diffs.sh 

if [ -d /autograder/results ]; then
    cp -v results.json /autograder/results/results.json
fi

cd ..