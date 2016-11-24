"""Provides Dataset class for handling datasets.

Dataset provides interface for managing data, eg normalization, batch building.
ICVLDataset, NYUDataset, MSRADataset are specific instances of different datasets.

Copyright 2015 Markus Oberweger, ICG,
Graz University of Technology <oberweger@icg.tugraz.at>

This file is part of SemiAutoAnno.

SemiAutoAnno is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SemiAutoAnno is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SemiAutoAnno.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy
from data import transformations
from data.basetypes import NamedImgSequence
from data.importers import Blender2Importer
from util.handdetector import HandDetector


__author__ = "Paul Wohlhart <wohlhart@icg.tugraz.at>, Markus Oberweger <oberweger@icg.tugraz.at>"
__copyright__ = "Copyright 2015, ICG, Graz University of Technology, Austria"
__credits__ = ["Paul Wohlhart", "Markus Oberweger"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Markus Oberweger"
__email__ = "oberweger@icg.tugraz.at"
__status__ = "Development"


class Dataset(object):
    """
    Base class for managing data. Used to create training batches.
    """

    def __init__(self, imgSeqs=None, localCache=True):
        """
        Constructor
        :param localCache: keeps image stacks locally for faster access, but might require more memory
        """
        self.localCache = localCache
        if imgSeqs is None:
            self._imgSeqs = []
        else:
            self._imgSeqs = imgSeqs
        self._imgStacks = {}
        self._dptStacks = {}
        self._labelStacks = {}

    @property
    def imgSeqs(self):
        return self._imgSeqs

    def imgSeq(self, seqName):
        for seq in self._imgSeqs:
            if seq.name == seqName:
                return seq
        return []

    @imgSeqs.setter
    def imgSeqs(self, value):
        self._imgSeqs = value
        self._imgStacks = {}
        self._dptStacks = {}

    def imgStackRGBOnly(self, seqName, normZeroOne=False):
        imgSeq = None
        for seq in self._imgSeqs:
            if seq.name == seqName:
                imgSeq = seq
                break
        if imgSeq is None:
            return []

        if seqName not in self._imgStacks:
            # compute the stack from the sequence
            numImgs = len(imgSeq.data)
            data0 = numpy.asarray(imgSeq.data[0].color, 'float32')
            label0 = numpy.asarray(imgSeq.data[0].gtorig, 'float32')
            h, w, _ = data0.shape
            j, d = label0.shape
            imgStack = numpy.zeros((numImgs, 3, h, w), dtype='float32')  # num_imgs,stack_size,rows,cols
            labelStack = numpy.zeros((numImgs, j, d), dtype='float32')  # num_imgs,joints,dim
            for i in xrange(numImgs):
                if normZeroOne:
                    imgRGB = numpy.asarray(imgSeq.data[i].color.copy(), 'float32')
                    imgRGB /= 256.
                else:
                    imgRGB = numpy.asarray(imgSeq.data[i].color.copy(), 'float32')
                    imgRGB -= 128.
                    imgRGB /= 128.

                imgStack[i] = imgRGB
                labelStack[i] = numpy.clip(numpy.asarray(imgSeq.data[i].gt3Dcrop, dtype='float32') / (imgSeq.config['cube'][2] / 2.), -1, 1)

            if self.localCache:
                self._imgStacks[seqName] = imgStack
                self._labelStacks[seqName] = labelStack
            else:
                return imgStack, labelStack

        return self._imgStacks[seqName], self._labelStacks[seqName]

    def imgStackDepthOnly(self, seqName, normZeroOne=False):
        imgSeq = None
        for seq in self._imgSeqs:
            if seq.name == seqName:
                imgSeq = seq
                break
        if imgSeq is None:
            return []

        if seqName not in self._dptStacks:
            # compute the stack from the sequence
            numImgs = len(imgSeq.data)
            data0 = numpy.asarray(imgSeq.data[0].dpt, 'float32')
            label0 = numpy.asarray(imgSeq.data[0].gtorig, 'float32')
            h, w = data0.shape
            j, d = label0.shape
            imgStack = numpy.zeros((numImgs, 1, h, w), dtype='float32')  # num_imgs,stack_size,rows,cols
            labelStack = numpy.zeros((numImgs, j, d), dtype='float32')  # num_imgs,joints,dim
            for i in xrange(numImgs):
                if normZeroOne:
                    imgD = numpy.asarray(imgSeq.data[i].dpt.copy(), 'float32')
                    imgD[imgD == 0] = imgSeq.data[i].com[2] + (imgSeq.config['cube'][2] / 2.)
                    imgD -= (imgSeq.data[i].com[2] - (imgSeq.config['cube'][2] / 2.))
                    imgD /= imgSeq.config['cube'][2]
                else:
                    imgD = numpy.asarray(imgSeq.data[i].dpt.copy(), 'float32')
                    imgD[imgD == 0] = imgSeq.data[i].com[2] + (imgSeq.config['cube'][2] / 2.)
                    imgD -= imgSeq.data[i].com[2]
                    imgD /= (imgSeq.config['cube'][2] / 2.)

                imgStack[i] = imgD
                labelStack[i] = numpy.clip(numpy.asarray(imgSeq.data[i].gt3Dcrop, dtype='float32') / (imgSeq.config['cube'][2] / 2.), -1, 1)

            if self.localCache:
                self._dptStacks[seqName] = imgStack
                self._labelStacks[seqName] = labelStack
            else:
                return imgStack, labelStack

        return self._dptStacks[seqName], self._labelStacks[seqName]


class Blender2Dataset(Dataset):
    def __init__(self, imgSeqs=None, basepath=None, localCache=True):
        """
        constructor
        """
        super(Blender2Dataset, self).__init__(imgSeqs, localCache)
        if basepath is None:
            basepath = '../../data/Blender/'

        self.lmi = Blender2Importer(basepath)

