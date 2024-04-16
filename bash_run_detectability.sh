#!/usr/bin/env bash
#SBATCH --time=01-00:00:00
#SBATCH -N 1 -n 16


##### Things to change:
##### 1. WORK_DIR (trial and inj)
##### 2. change environment

#OUT_DIR=custom_corner
WORK_DIR=/vol/astro8/alevan/kkrishna/honors_project/winter_strategy
SCRATCH_DIR=/scratch/kkrishna
ENV=ghosh_sky_tiling

# -- function to create a new directory with unique name
# -- note: avoid the '-p' option with mkdir;

mkdir_uniq () {
    local i path=$1
    for i in {0..800}; do
        NEWDIR=$path/$i
        mkdir $NEWDIR && break
    done
    errmsg="too many directories in $path"
    [[ $i -eq 800 ]] && { echo $errmsg; exit 1; }
    return 0
}

# -- record what this script does
set -x 

# -- to make sure that /scratch/$USER already exists at comaN node
mkdir -p $SCRATCH_DIR || exit 1

#-- setup new scratch space
mkdir_uniq ${SCRATCH_DIR} || exit 1
SCRATCH_DIR=$NEWDIR
#-- change directory to scratch space
errmsg="directory $SCRATCH_DIR not available"
cd $SCRATCH_DIR || { echo $errmsg; exit 1; }

#-- Copy code from permanent storage to coma computation node
scp -vr coma:$WORK_DIR/* ./ 2>/dev/null
#scp -vr coma:$WORK_DIR/$OUT_DIR ./ 2>/dev/null

chmod u+x -R *

source activate $ENV

###################################################################################################################

python ./galaxy_targeted_detectability.py
#python ./galaxy_informed_tiling_scheduling.py

####################################################################################################################

SIM_EXITSTAT=$?

#-- Copy data back to permanent storage:
rsync -avrP $SCRATCH_DIR/* coma:$WORK_DIR 2>/dev/null

exit $SIM_EXITSTAT
