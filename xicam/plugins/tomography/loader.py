# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import copy
from pipeline.loader import StackImage, PStack
import numpy as np
__author__ = "Luis Barroso-Luque"
__copyright__ = "Copyright 2016, CAMERA, LBL, ALS"
__credits__ = ["Ronald J Pandolfi", "Dinesh Kumar", "Singanallur Venkatakrishnan", "Luis Luque", "Alexander Hexemer"]
__license__ = ""
__version__ = "1.2.1"
__maintainer__ = "Ronald J Pandolfi"
__email__ = "ronpandolfi@lbl.gov"
__status__ = "Beta"


class ProjectionStack(StackImage):
    """
    Simply subclass of StackImage for Tomography Projection stacks.

    Attributes
    ----------
    flats : ndarray
        Flat field data
    darks : ndarray
        Dark field data
    """

    def __init__(self, filepath=None, data=None):
        super(ProjectionStack, self).__init__(filepath=filepath, data=data)
        try:
            self.flats = self.fabimage.flats
            self.darks = self.fabimage.darks
        except AttributeError:
            self.flats, self.darks = None, None

    def _getframe(self, frame=None):
        return super(ProjectionStack, self)._getframe(frame=frame).transpose()


class SinogramStack(StackImage):
    """
    Simply subclass of StackImage for Tomography Sinogram stacks.

    TODO:
      - make sure flats / darks are handled correctly
    """

    def __init__(self, filepath=None, data=None):
        super(SinogramStack, self).__init__(filepath=filepath, data=data)
        self._cachesize = 10

    def __new__(cls):
        cls.invalidatecache()

    @classmethod
    def cast(cls, obj):
        """
        Use this to cast a ProjectionStack into a SinogramStack

        Parameters
        ----------
        obj : StackImage/ProjectionStack
            Instance object to cast into Sinogram stack
        Returns
        -------
        SinogramStack
            Object cast into SinogramStack
        """
        new_obj = copy(obj)
        new_obj.__class__ = cls
        new_obj.shape = new_obj.shape[2], new_obj.shape[0], new_obj.shape[1]
        return new_obj

    def _getimage(self, frame):
        """
        Override method from base class to read along sinogram dimension
        """
        return self.fabimage[:, frame, :]


    def _getframe(self, frame=None):
        return super(SinogramStack, self)._getframe(frame=frame).transpose()
