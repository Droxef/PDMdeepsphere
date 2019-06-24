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
# from grid import pgrid
import hyperparameters


def single_experiment(sigma, order, sigma_noise, experiment_type):

    ename = '_'+experiment_type

    Nside = 1024

    EXP_NAME = '40sim_{}sides_{}noise_{}order_{}sigma{}'.format(
        Nside, sigma_noise, order, sigma, ename)

    data_path = '/mnt/scratch/lts2/mdeff/deepsphere/data/'
    x_raw_train, labels_raw_train, x_raw_std = experiment_helper.get_training_data(sigma, order, data_path=data_path+'same_psd/')
    x_raw_test, labels_test, _ = experiment_helper.get_testing_data(sigma, order, sigma_noise, x_raw_std, data_path=data_path)

    ret = experiment_helper.data_preprossing(x_raw_train, labels_raw_train, x_raw_test, sigma_noise, feature_type=None)
    features_train, labels_train, features_validation, labels_validation, features_test = ret

    training = LabeledDatasetWithNoise(features_train, labels_train, end_level=sigma_noise)
    validation = LabeledDataset(features_validation, labels_validation)

    params = hyperparameters.get_params(training.N, EXP_NAME, order, Nside, experiment_type)
    model = models.deepsphere(**params)

    # Cleanup before running again.
    shutil.rmtree('summaries/{}/'.format(EXP_NAME), ignore_errors=True)
    shutil.rmtree('checkpoints/{}/'.format(EXP_NAME), ignore_errors=True)

    print(model.fit(training, validation))

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
        time.sleep(np.random.rand()*10)
        res = single_experiment(sigma, order, sigma_noise, experiment_type)
        filepath = os.path.join(path, 'deepsphere_results_list_sigma{}{}'.format(sigma,ename))
        new_data = [order, sigma_noise, res]
        if os.path.isfile(filepath+'.npz'):
            results = np.load(filepath+'.npz')['data'].tolist()
        else:
            results = []
        results.append(new_data)
        np.savez(filepath, data=results)