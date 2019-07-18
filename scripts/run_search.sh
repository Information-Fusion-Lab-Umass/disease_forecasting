#!/bin/bash
#
#SBATCH --job-name=T3-confirm
#SBATCH -o misc/run_outputs/%j.txt            # output file
#SBATCH -e misc/errors/%j.err            # File to which STDERR will be written
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=120000    # Memory in MB per cpu allocated
#SBATCH --gres=gpu:4
#SBATCH --time=4-00:00:00          # HH:MM:SS

python3 main_randomized_search.py --config=../configs/flare_skorch_covtest.yaml --debug=0 --numT=2 --n_iter=40 --exp_id=T2_40_covtest_dp_epoch50
sleep 1
exit
