#!/usr/bin/env python3
# coding: utf-8

import sys
from SHREC17.load_shrec import fix_dataset, Shrec17Dataset

data_path = '../data/shrec17/'

if len(sys.argv) > 4:
    data_path = sys.argv[1]
    experiment = sys.argv[2]
    nside = sys.argv[3]
    augmentation = sys.argv[4]
else:
    nside = 32
    augmentation = 3
    data_path = '../data/shrec17/'
    experiment = 'deepsphere_norot'

Shrec17Dataset(data_path, 'train', nside=nside, augmentation=augmentation, experiment = experiment, verbose=False)
#fix_dataset(data_path+'val_perturbed')
Shrec17Dataset(data_path, 'val', perturbed=True, nside=nside, augmentation=augmentation, experiment = experiment, verbose=False)
#fix_dataset(data_path+'test_perturbed')
Shrec17Dataset(data_path, 'test', nside=nside, augmentation=augmentation, experiment = experiment, verbose=False)