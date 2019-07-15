import sys
import unittest
from unittest import TestCase as test
sys.path.append('..')
import os
import yaml
import argparse
from shutil import copyfile
#import ipdb
from time import time
import pickle
import numpy as np
from src import datagen, utils, engine, evaluate
from src import forecastNet
import copy
from skorch import NeuralNetClassifier
from skorch.callbacks import EpochScoring
from sklearn.metrics import f1_score, roc_auc_score,make_scorer
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import torch
import torch.nn as nn
from scipy.stats import expon


import ipdb


#  os.environ['CUDA_VISIBLE_DEVICES']=''

def main(config_file):
    # Parser config file
    with open(config_file) as f:
        config = yaml.load(f)

    main_exp_dir = os.path.join(config['output_dir'], config['exp_id'])


    utils.create_dirs([config['output_dir'], main_exp_dir, os.path.join(main_exp_dir, 'results'), os.path.join(main_exp_dir, 'logs')])


    max_T = config['datagen']['max_T'] # Load data and get image paths
    num_classes = config['model']['module__task']['params']['num_classes'] 

    t = time()
    path_load = config['data'].pop('path_load')
    if os.path.exists(path_load):
        with open(path_load, 'rb') as f:
            data = pickle.load(f)
    else:
        data = datagen.get_data(**config['data'])
        with open(path_load, 'wb') as f:
            pickle.dump(data, f)
    print('Data Loaded : ', time()-t)
    print('Basic Data Stats:')
    print('Number of patients = ', len(data) - 2)

    # Datagens
    t = time()


    # Catch dataset_size % batch_size == 1 issue with batchnorm 1d:

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda:0" if use_cuda else "cpu")

    datagen_all, datasets_all, data_train_size = \
            datagen.get_datagen(data, **config['datagen'])
    print('Datagens Loaded : ', time()-t)
    class_wt = utils.get_classWeights(data, config['data']['train_ids_path'])
    print(class_wt)

    num_iter = config['num_iter']

    model_list = [None]*num_iter
    val_cnfmats = [None]*num_iter
    train_cnfmats = [None]*num_iter 

    for iteration in range(num_iter):
        model_config = copy.deepcopy(config['model'])

        print('Iteration: {}'.format(iteration))
        # Create experiment output directories
        exp_dir = os.path.join(main_exp_dir, config['exp_id'] + '_' + str(iteration))
        utils.create_dirs([config['output_dir'], exp_dir,
                os.path.join(exp_dir, 'checkpoints'),
                os.path.join(exp_dir, 'results'),
                os.path.join(exp_dir, 'logs')])

        # Copy config file
#        copyfile(config_file, os.path.join(exp_dir, config['exp_id']+'_' + str(iteration) + '.yaml'))
        with open(os.path.join(exp_dir, config['exp_id']+'_' + str(iteration) + '.yaml'),'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        # Define Classification model
        #model = engine.Engine(class_wt, model_config)
        #model_list[iteration] = model

        load_model = model_config.pop('load_model')
        early_stopping = model_config.pop('early_stopping')
        lr = model_config.pop('learning_rate')
        weight_decay = model_config.pop('weight_decay')

        device = torch.device("cpu")
        init = model_config.pop('init')
        
        # Define randomized search parameters
        params = {
        #            'max_epochs': [15,20,25,30,35,40],
                    'optimizer__lr': [.001],
                    'optimizer__weight_decay': [.001,.008]
                 }
        
        # Define sklearn wrapper and scoring function

        f1_scorer = make_scorer(f1_score, average = 'macro')
        auc = EpochScoring(scoring='roc_auc', lower_is_better=True)
        f1 = EpochScoring(scoring=f1_scorer,lower_is_better=False)
        net = forecastNet.forecastNet(
                engine.Model, 
                max_epochs=50,
                batch_size=128,
                device = device,
       #         lr=0.001,
                callbacks = [f1],
                optimizer=torch.optim.Adam,
                criterion=nn.CrossEntropyLoss,
                **model_config,
                module__device=device,
                module__class_wt=class_wt
            )
        X,Y = datasets_all[0].return_all()

        gs = GridSearchCV(net, params, cv=3, scoring=f1_scorer, verbose=1)


        print('Grid Search!')
        gs.fit(X,Y)

        print(gs.best_score_, gs.best_params_)

    if(num_iter > 1):
        print('Calculating aggregate results...')
        agg_metrics = utils.calculate_averages(val_cnfmats)
        agg_mat = evaluate.ConfMatrix(max_T-1,num_classes)
        agg_mat.set_vals(agg_metrics)
        agg_mat.save(main_exp_dir,'agg')
        with open(os.path.join(main_exp_dir,'results/agg_metrics_dict.pickle'),'wb') as f:
            pickle.dump(agg_metrics,f)

#    return datagen_train, datagen_val


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='../configs/config.yaml')
    args = parser.parse_args()
    dgt, dgv = main(args.config)