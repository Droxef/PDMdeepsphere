#!/usr/bin/env python3
# coding: utf-8

"""
Script to run the DeepSphere experiment.
Both the fully convolutional (FCN) and the classic (CNN) architecture variants
are supported.
"""

import os
import shutil
import sys

import numpy as np
import time

from deepsphere import models, experiment_helper
from deepsphere.data import LabeledDatasetWithNoise, LabeledDataset
from grid import pgrid
import hyperparameters


def single_experiment(sigma, order, sigma_noise, experiment_type):

    ename = '_'+experiment_type

    Nside = 1024

    EXP_NAME = '40sim_{}sides_{}noise_{}order_{}sigma{}'.format(
        Nside, sigma_noise, order, sigma, ename)

    input("gathering data")

    x_raw_train, labels_raw_train, x_raw_std = experiment_helper.get_training_data(sigma, order)
    x_raw_test, labels_test, _ = experiment_helper.get_testing_data(sigma, order, sigma_noise, x_raw_std)

    print(x_raw_train.shape)    # 1920 x 262144

    #x_raw_train=np.concatenate([x_raw_train[:5,...],x_raw_train[-5:,...]])
    #labels_raw_train=np.concatenate([labels_raw_train[:5],labels_raw_train[-5:]])
    #x_raw_test=np.concatenate([x_raw_test[:5,...],x_raw_test[-5:,...]])
    #labels_test=np.concatenate([labels_test[:5],labels_test[-5:]])

    input("preprocess data")

    ret = experiment_helper.data_preprossing(x_raw_train, labels_raw_train, x_raw_test, sigma_noise, feature_type=None)
    features_train, labels_train, features_validation, labels_validation, features_test = ret

    print(features_train.shape) # 1536 x 262144 ( nbr elem x nbr pixels)

    input("add noise")

    training = LabeledDatasetWithNoise(features_train, labels_train, end_level=sigma_noise)
    validation = LabeledDataset(features_validation, labels_validation)

    input("create model")

    params = hyperparameters.get_params(training.N, EXP_NAME, order, Nside, experiment_type)
    model = models.deepsphere(**params)

    input("rmtree")

    # Cleanup before running again.
    shutil.rmtree('summaries/{}/'.format(EXP_NAME), ignore_errors=True)
    shutil.rmtree('checkpoints/{}/'.format(EXP_NAME), ignore_errors=True)

    input("fit")

    model.fit(training, validation)

    input("error")

    error_validation = experiment_helper.model_error(model, features_validation, labels_validation)
    print('The validation error is {}%'.format(error_validation * 100), flush=True)

    error_test = experiment_helper.model_error(model, features_test, labels_test)
    print('The testing error is {}%'.format(error_test * 100), flush=True)

    return error_test


if __name__ == '__main__':

    if len(sys.argv) > 1:
        experiment_type = sys.argv[1]
    else:
        experiment_type = 'FCN' # 'CNN'

    if len(sys.argv) > 2:
        sigma = int(sys.argv[2])
        order = int(sys.argv[3])
        sigma_noise = float(sys.argv[4])
        grid = [(sigma, order, sigma_noise)]
    else:
        grid = pgrid()

    ename = '_'+experiment_type

    path = 'results/deepsphere/'
    os.makedirs(path, exist_ok=True)

    for sigma, order, sigma_noise in grid:
        print('Launch experiment for sigma={}, order={}, noise={}'.format(sigma, order, sigma_noise))
        # avoid all jobs starting at the same time
        time.sleep(np.random.rand()*100)
        res = single_experiment(sigma, order, sigma_noise, experiment_type)
        filepath = os.path.join(path, 'deepsphere_results_list_sigma{}{}'.format(sigma,ename))
        new_data = [order, sigma_noise, res]
        if os.path.isfile(filepath+'.npz'):
            results = np.load(filepath+'.npz')['data'].tolist()
        else:
            results = []
        results.append(new_data)
        np.savez(filepath, data=results)
