#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import sys
sys.path.append('../..')

os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # change to chosen GPU to use, nothing if work on CPU

import numpy as np
import time
import matplotlib.pyplot as plt
import h5py

from tqdm import tqdm
from mpl_toolkits.mplot3d import Axes3D
# import cartopy.crs as ccrs

from deepsphere import models
from ClimateDataLoader import EquiangularDataset
from pygsp.graphs import SphereEquiangular

from sklearn.metrics import accuracy_score, average_precision_score
from sklearn.preprocessing import label_binarize

def accuracy(pred_cls, true_cls, nclass=3):
    accu = []
    tot_int = 0
    tot_cl = 0
    for i in range(3):
        intersect = np.sum(((pred_cls == i) * (true_cls == i)))
        thiscls = np.sum(true_cls == i)
        accu.append(intersect / thiscls * 100)
        tot_int += intersect
        tot_cl += thiscls
    return np.array(accu), np.mean(accu) # , tot_int/tot_cl * 100

def average_precision(score_cls, true_cls, nclass=3):
    score = score_cls
    true = label_binarize(true_cls.reshape(-1), classes=[0, 1, 2])
    score = score.reshape(-1, nclass)
    return average_precision_score(true, score, None)

if __name__ == '__main__':
    sampling = 'equiangular'
    filepath = 'results_equiangular'
    
    flat = False
    
    path = '../../data/Climate/'
    g = SphereEquiangular(bandwidth=(384, 576), sampling='SOFT')
    glong, glat = np.rad2deg(g.long), np.rad2deg(g.lat)
    del g
    
    training = EquiangularDataset(path, 'train', s3=False)
    validation = EquiangularDataset(path, 'val', s3=False)
    test = EquiangularDataset(path, 'test', s3=False)
    
    EXP_NAME = 'Climate_pooling_weight_{}'.format(sampling)
    
    # Cleanup before running again.
    shutil.rmtree('../../summaries/{}/'.format(EXP_NAME), ignore_errors=True)
    shutil.rmtree('../../checkpoints/{}/'.format(EXP_NAME), ignore_errors=True)
    
    import tensorflow as tf
    if flat:
        params = {'nsides': [(bw1, bw2), (bw1, bw2), (bw1, bw2), (bw1, bw2)],
                  'F': [16, 64, 128],#np.max(labels_train).astype(int)+1],
                  'K': [5]*3,
                  'batch_norm': [True]*3}
    else:
        params = {'nsides': [(384, 576), (384, 576), (384//4, 576//4), (384//16, 576//16), (384//32, 576//16)],
                  'F': [8, 32, 64, 128],
                  'K': [5]*4,
                  'batch_norm': [True]*4}
    params['sampling'] = sampling
    params['dir_name'] = EXP_NAME
    params['num_feat_in'] = 16
    params['conv'] = 'chebyshev5'
    params['pool'] = 'average'
    params['activation'] = 'relu'
    params['statistics'] = None # 'mean'
    params['regularization'] = 0
    params['dropout'] = 1
    params['num_epochs'] = 30  # Number of passes through the training data.
    params['batch_size'] = 1
    params['scheduler'] = lambda step: tf.train.exponential_decay(1e-3, step, decay_steps=2000, decay_rate=1)
    #params['optimizer'] = lambda lr: tf.train.GradientDescentOptimizer(lr)
    parmas['optimizer'] = lambda lr: tf.train.AdamOptimizer(lr, beta1=0.9, beta2=0.999, epsilon=1e-8)
#     params['optimizer'] = lambda lr: tf.train.RMSPropOptimizer(lr, decay=0.9, momentum=0.)
    n_evaluations = 15
    params['eval_frequency'] = int(params['num_epochs'] * (training.N) / params['batch_size'] / n_evaluations)
    params['M'] = []
    params['Fseg'] = 3
    params['dense'] = True
    params['weighted'] = True
#     params['profile'] = True
    params['tf_dataset'] = training.get_dataset(params['batch_size'])
    
    model = models.deepsphere(**params)
    
    acc_val, loss_val, loss_train, t_step, t_batch = model.fit(training, validation, use_tf_dataset=True, cache='TF')
    
    probabilities, _, _ = model.probs(test, 3, cache='TF')
    predictions, labels_test, loss = model.predict(test, cache='TF')
    
    AP = average_precision(probabilities, labels_test)
    mAP = np.mean(AP[1:])
    acc, macc = accuracy(predictions, labels_test)
    
    if os.path.isfile(filepath+'.npz'):
        file = np.load(filepath+'.npz')
        tb = file['tbatch'].tolist()
        avprec = file['AP'].tolist()
        accuracy = file['acc'].tolist()
    else:
        tb = []
        avprec = []
        accuracy = []
    tb.append(t_batch)
    avprec.append([*AP, mAP])
    accuracy.append([*acc, macc])
    np.savez(filepath, AP=avprec, acc=accuracy, tbatch=tb)