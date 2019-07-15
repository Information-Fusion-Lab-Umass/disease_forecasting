#!/bin/bash
#
#SBATCH --job-name=debug
#SBATCH -o misc/run_outputs/%j.txt            # output file
#SBATCH -e misc/errors/%j.err            # File to which STDERR will be written
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=120000    # Memory in MB per cpu allocated
#SBATCH --gres=gpu:4
#SBATCH --time=4-00:00:00          # HH:MM:SS

python3 main_randomized_search.py --config=../configs/flare_skorch.yaml --debug=1 --numT=4 --n_iter=1
sleep 1
exit