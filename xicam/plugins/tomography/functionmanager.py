# -*- coding: utf-8 -*-


__author__ = "Luis Barroso-Luque"
__copyright__ = "Copyright 2016, CAMERA, LBL, ALS"
__credits__ = ["Ronald J Pandolfi", "Dinesh Kumar", "Singanallur Venkatakrishnan", "Luis Luque", "Alexander Hexemer"]
__license__ = ""
__version__ = "1.2.1"
__maintainer__ = "Ronald J Pandolfi"
__email__ = "ronpandolfi@lbl.gov"
__status__ = "Beta"


import inspect
import time
import os
from collections import OrderedDict
from copy import deepcopy
from modpkgs import yamlmod
import numpy as np
import pyqtgraph as pg
from PySide import QtCore, QtGui
from pyqtgraph.parametertree import Parameter
from . import config
from . import reconpkg
from . import functionwidgets as fc
from xicam.widgets import featurewidgets as fw

class TestRangeDialog(QtGui.QDialog):
    """
    Simple QDialog subclass with three spinBoxes to inter start, end, step for a range to test a particular function
    parameter
    """

    def __init__(self, dtype, prange, **opts):
        super(TestRangeDialog, self).__init__(**opts)
        SpinBox = QtGui.QSpinBox if dtype == 'int' else QtGui.QDoubleSpinBox
        self.gridLayout = QtGui.QGridLayout(self)
        self.spinBox = SpinBox(self)
        self.gridLayout.addWidget(self.spinBox, 1, 0, 1, 1)
        self.spinBox_2 = SpinBox(self)
        self.gridLayout.addWidget(self.spinBox_2, 1, 1, 1, 1)
        self.spinBox_3 = SpinBox(self)
        self.gridLayout.addWidget(self.spinBox_3, 1, 2, 1, 1)
        self.label = QtGui.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.gridLayout.addWidget(self.label_2, 0, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self)
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.gridLayout.addWidget(self.label_3, 0, 2, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Ok)
        self.gridLayout.addWidget(self.buttonBox, 0, 3, 2, 1)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        if prange is not (None, None, None):
            self.spinBox.setMaximum(9999)  # 3 * prange[2])
            self.spinBox_2.setMaximum(9999)  # 3 * prange[2])
            self.spinBox_3.setMaximum(9999)  # prange[2])

            self.spinBox.setValue(prange[0])
            self.spinBox_2.setValue(prange[1])
            self.spinBox_3.setValue(prange[2])

        self.setWindowTitle("Set parameter range")
        self.label.setText("Start")
        self.label_2.setText("End")
        self.label_3.setText("Step")

    def selectedRange(self):
        # return the end as selected end + step so that the range includes the end
        return np.arange(self.spinBox.value(), self.spinBox_2.value(), self.spinBox_3.value())


class TestListRangeDialog(QtGui.QDialog):
    """
    Simple QDialog subclass with comboBox and lineEdit to choose from a list of available function parameter keywords
    in order to test the different function parameters.
    """

    def __init__(self, options, **opts):
        super(TestListRangeDialog, self).__init__(**opts)
        self.gridLayout = QtGui.QGridLayout(self)
        self.comboBox = QtGui.QComboBox(self)
        self.gridLayout.addWidget(self.comboBox, 1, 0, 1, 1)
        self.lineEdit = QtGui.QLineEdit(self)
        self.lineEdit.setReadOnly(True)
        self.gridLayout.addWidget(self.lineEdit, 2, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Ok)
        self.gridLayout.addWidget(self.buttonBox, 1, 1, 2, 1)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle('Set parameter range')

        self.options = options
        self.comboBox.addItems(options)
        self.comboBox.activated.connect(self.addToList)
        self.lineEdit.setText(' '.join(options))
        self.lineEdit.keyPressEvent = self.keyPressEvent

    def addToList(self, option):
        self.lineEdit.setText(str(self.lineEdit.text()) + ' ' + self.options[option])

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Backspace or ev.key() == QtCore.Qt.Key_Delete:
            self.lineEdit.setText(' '.join(str(self.lineEdit.text()).split(' ')[:-1]))
        elif ev.key() == QtCore.Qt.Key_Enter or ev.key() == QtCore.Qt.Key_Return:
            self.addToList(self.comboBox.currentIndex())
        ev.accept()

    def selectedRange(self):
        return str(self.lineEdit.text()).split(' ')


class FunctionManager(fw.FeatureManager):
    """
    Subclass of FeatureManager used to manage tomography workflow/pipeline FunctionWidgets

    Attributes
    ----------
    cor_offest : function/lambda
        function to correct for an offset in the COR location. As when padding the input array
    corr_scale : function/lambda
        function to correct for a scaling in the COR location. As when subsampling the input array

    recon_function : FunctionWidget
        FunctionWidget representing the Reconstruction Function in worflow pipeline

    Parameters
    ----------
    list_layout : QtGui.QLayout
        Layout to display the list of FunctionWidgets
    form_layout : QtGui.QLayout
        Layout to display the FunctionWidgets form (pyqtgraph.Parameter)
    function_widgets : list of FunctionWidgets, optional
        List with functionwidgets for initialization
    blank_form : QtGui.QWidget, optional
        Widget to display in form_layout when not FunctionWidget is selected

    Signals
    -------
    sigTestRange(str, object, dict)
    sigPipelineChanged()
        Emitted when the pipeline changes or the reconstruction function is changed
    """

    sigTestRange = QtCore.Signal(str, object, dict)
    sigPipelineChanged = QtCore.Signal()
    sigCORDetectChanged = QtCore.Signal(bool)

    center_func_slc = {'Phase Correlation': (0, -1)}  # slice parameters for center functions
    mask_functions = ['F3D Mask Filter', 'F3D MM Erosion', 'F3D MM Dilation', 'F3D MM Opening', 'F3D MM Closing']

    def __init__(self, list_layout, form_layout, function_widgets=None, blank_form=None):
        super(FunctionManager, self).__init__(list_layout, form_layout, feature_widgets=function_widgets,
                                              blank_form=blank_form)
        #TODO: add attribute to keep track of function's order in pipeline
        self.cor_offset = lambda x: x  # dummy
        self.cor_scale = lambda x: x  # dummy
        self.recon_function = None



    # TODO fix this astra check raise error if package not available
    def addFunction(self, function, subfunction, package):
        """
        Adds a Function to the workflow pipeline

        Parameters
        ----------
        function : str
            generic name of function
        subfunction : str
            specific name of function under the generic name category
        package : python package
            package where function is defined
        """
        if function == 'Reconstruction':
            if 'astra' in reconpkg.packages and package == reconpkg.packages['astra']:
                func_widget = fc.AstraReconFuncWidget(function, subfunction, package)
            elif 'mbir' in reconpkg.packages and package == reconpkg.packages['mbir']:
                func_widget = fc.TomoCamReconFuncWidget(function, subfunction, package)
            else:
                func_widget = fc.TomoPyReconFunctionWidget(function, subfunction, package)
            self.recon_function = func_widget
            func_widget.input_functions['center'].previewButton.clicked.connect(self.CORChoiceUpdated)
            self.sigPipelineChanged.emit()
        elif function == 'Filter' and subfunction in self.mask_functions:
            func_widget = fc.MaskFunctionWidget(function, subfunction, package)
        elif function == 'Reader':
            func_widget = fc.ReadFunctionWidget(function, subfunction, package)
        elif function == 'Write':
            func_widget = fc.WriteFunctionWidget(function, subfunction, package)
        else:
            func_widget = fc.FunctionWidget(function, subfunction, package)
        func_widget.sigTestRange.connect(self.testParameterRange)
        self.addFeature(func_widget)

        if function == 'Padding' or function  == 'Crop':
            self.connectCropPad()

        return func_widget

    def connectCropPad(self):
        names = [func.name for func in self.features]
        if 'Padding' in names and 'Crop' in names:
            for feature in self.features:
                if feature.func_name == 'Padding': pad = feature
                elif feature. func_name == 'Crop': crop = feature

            pad.params.child('npad').sigValueChanged.connect(lambda x: crop.params.child('p11').setValue(x.value()))
            pad.params.child('npad').sigValueChanged.connect(lambda x: crop.params.child('p12').setValue(x.value()))
            pad.params.child('npad').sigValueChanged.connect(lambda x: crop.params.child('p21').setValue(x.value()))
            pad.params.child('npad').sigValueChanged.connect(lambda x: crop.params.child('p22').setValue(x.value()))

            children = [crop.params.child('p11'), crop.params.child('p21'), crop.params.child('p12'), crop.params.child('p22')]
            for p in children:
                for p_other in [param for param in children if param != p]:
                    p.sigValueChanged.connect(lambda x=p: p_other.setValue(x.value()))
                p.sigValueChanged.connect(lambda x: pad.params.child('npad').setValue(x.value()))

    def addInputFunction(self, funcwidget, parameter, function, subfunction, package, **kwargs):
        """
        Adds an input function to the give function widget

        Parameters
        ----------
        funcwidget : FunctionWidget
            Widget to add subfunction to
        parameter : str
            Parameter name that will be overriden by return value of input function
        function : str
            generic name of function
        subfunction : str
            specific name of function under the generic name category
        package : python package
            package where function is defined
        kwargs
            Additional keyword arguments
        """
        try:
            ipf_widget = fc.FunctionWidget(function, subfunction, package, **kwargs)
            funcwidget.addInputFunction(parameter, ipf_widget)
        except AttributeError:
            ipf_widget = funcwidget.input_functions[parameter]
        return ipf_widget

    def updateCORChoice(self, boolean):
        for feature in self.features:
            if 'center' in feature.input_functions:
                feature.input_functions['center'].enabled = boolean

    def updateCORFunc(self, func, widget):
        for feature in self.features:
            if 'center' in feature.input_functions:
                feature.removeInputFunction('center')
                feature.addCenterDetectFunction("Center Detection", func, package=reconpkg.packages['tomopy'])
                self.cor_func = feature.input_functions['center']
                self.cor_widget = widget
                for child in widget.params.children():
                    child.sigValueChanged.connect(self.updateCORPipeline)
                for child in self.cor_func.params.children():
                    child.sigValueChanged.connect(self.updateCORWidget)


    # slot for connecting cor widget and pipeline cor
    def updateCORPipeline(self, param):
        child = self.cor_func.params.child(param.name())
        child.setValue(param.value())

    # slot for connecting cor widget and pipeline cor
    def updateCORWidget(self, param):
        child = self.cor_widget.params.child(param.name())
        child.setValue(param.value())


    def CORChoiceUpdated(self):
        for feature in self.features:
            if 'center' in feature.input_functions:
                self.sigCORDetectChanged.emit(feature.input_functions['center'].enabled)
    #
    # if parameter in self.input_functions:  # Check to see if parameter already has input function
    #     if functionwidget.subfunc_name == self.input_functions[parameter].subfunc_name:
    #         raise AttributeError('Input function already exists')  # skip if the input function already exists
    #     self.removeInputFunction(parameter)  # Remove it if it will be replaced
    # self.input_functions[parameter] = functionwidget
    # self.addSubFeature(functionwidget)
    # functionwidget.sigDelete.connect(lambda: self.removeInputFunction(parameter))

    def updateParameters(self):
        """
        Updates all parameters for the current function list
        """
        for function in self.features:
            function.updateParamsDict()

    def connectReaderROI(self, roi_widget):
        roi_widget.sigRegionChanged.connect(self.adjustReaderParams)

    def adjustReaderParams(self, roi_widget):
        for feature in self.features:
            if 'Reader' in feature.name:
                pos = roi_widget.pos()
                size = roi_widget.size()
                x1 = int(pos[0]) if pos[0]>0 else 0
                x2 = int(pos[0]+size[0]) if pos[0]+size[0]<feature.params.child('end_width').defaultValue() else \
                        feature.params.child('end_width').defaultValue()
                y1 = int(pos[1]) if pos[1]>0 else 0
                y2 = int(pos[1]+size[1]) if pos[1]+size[1]<feature.params.child('end_sinogram').defaultValue() else \
                        feature.params.child('end_sinogram').defaultValue()

                feature.params.child('start_width').setValue(x1)
                feature.params.child('end_width').setValue(x2)
                feature.params.child('start_sinogram').setValue(y1)
                feature.params.child('end_sinogram').setValue(y2)


    def lockParams(self, boolean):
        """
        Locks all parameters for the current function list
        """
        for func in self.features:
            func.allReadOnly(boolean)

    def resetCenterCorrection(self):
        """
        Resets the center correction functions to dummy lambdas
        """
        self.cor_offset = lambda x: x  # dummy
        self.cor_scale = lambda x: x  # dummy

    def setCenterCorrection(self, name, param_dict):
        """
        Sets the center correction lambda's according to the effect of function given to the input array

        Parameters
        ----------
        name : str
            Name of function that has an effect on the COR value
        param_dict : dict
            Parameter dictionary of the function give
        """

        if 'Reader' in name:
            for feature in self.features:
                if 'Reader' in feature.name:
                    n = int(feature.params.child('start_width').value())
                    dummy = self.cor_offset
                    self.cor_offset = lambda x: dummy(x) - n
        elif 'Padding' in name and param_dict['axis'] == 2:
            n = param_dict['npad']
            dummy = self.cor_offset
            self.cor_offset = lambda x: dummy(x) + n
        elif 'Downsample' in name and param_dict['axis'] == 2:
            s = param_dict['level']
            self.cor_scale = lambda x: x / 2 ** s
        elif 'Upsample' in name and param_dict['axis'] == 2:
            s = param_dict['level']
            self.cor_scale = lambda x: x * 2 ** s

    def saveState(self, datawidget):
        """
        Parameters
        ----------

        datawidget : QWidget
            QWidget (usually in the form of a TomoViewer) that holds data

        Returns
        -------
        run_state : list of four elements representing data necessary for reconstruction
            * lst: list of functools.partial which represent the function pipeline
            * theta: array of 'theta' values which represent the angles at which tomography data was taken
            * center: the center of rotation of the data
            * a string of function names and parameters to be later written into a yaml file
        """

        # extract function pipeline
        lst = []; theta = []
        for function in self.features:
            if not function.enabled or 'Reader' in function.name:
                continue
            fpartial = function.partial
            # set keywords that will be adjusted later by input functions or users
            for arg in inspect.getargspec(function._function)[0]:
                if arg not in fpartial.keywords.keys() or arg in 'center':
                    fpartial.keywords[arg] = '{}'.format(arg)

            # get rid of degenerate keyword arguments
            if 'arr' in fpartial.keywords and 'tomo' in fpartial.keywords:
                fpartial.keywords['tomo'] = fpartial.keywords['arr']
                fpartial.keywords.pop('arr', None)

            # special cases for the 'write' function
            if 'start' in fpartial.keywords:
                fpartial.keywords['start'] = 'start'
            if 'Write' in function.name:
                fpartial.keywords.pop('parent folder', None)
                fpartial.keywords.pop('folder name', None)
                fpartial.keywords.pop('file name', None)

            lst.append((fpartial, function.name))

            if 'Reconstruction' in function.name: # could be bad, depending on if other operations need theta/center
                for param,ipf in function.input_functions.items():
                    if not ipf.enabled:
                        if 'center' in param:
                            center = function.partial.keywords['center']
                        continue
                    # extract center value
                    if 'center' in param:
                        # this portion is taken from old updateFunctionPartial code
                        args = []
                        if ipf.subfunc_name in FunctionManager.center_func_slc:
                            args = list(map(datawidget.data.fabimage.__getitem__,
                                                         FunctionManager.center_func_slc[ipf.subfunc_name]))
                        else:
                            args.append(datawidget.getsino())
                        if ipf.subfunc_name == 'Nelder-Mead':
                            args.append(function.input_functions['theta'].partial())
                            # ipf.partial.keywords['theta'] = function.input_functions['theta'].partial()
                        center = ipf.partial(*args)

                    # extract theta values
                    if 'theta' in param:
                        theta = ipf.partial()

        extract = (config.extract_pipeline_dict(self.features), config.extract_runnable_dict(self.features))
        return [lst, theta, center, extract]

    def loadDataDictionary(self, datawidget, theta, center, slc = None):
        """
        Method to load dictionary of data relevant to a reconstruction

        Parameters
        ----------
        datawidget : QWidget
            QWidget (usually in the form of a TomoViewer) that holds data
        theta : array
            Array of values which represent angles at which tomography data was taken
        center : float
            Center of rotation of data
        slc : Slice
            Slice object to extract relevant portions of sinogram/flats/darks data

        Returns
        -------
        data_dict : dict
            Dictionary of data relevant to reconstruction
        """

        data_dict = OrderedDict()

        data_dict['tomo'] = datawidget.getsino(slc=slc)
        if datawidget.data.flats is not None:
            data_dict['flats'] = datawidget.getflats(slc=slc)
        if datawidget.data.darks is not None:
            data_dict['dark'] = datawidget.getdarks(slc=slc)

        try:
            if slc is not None and slc[0].start is not None:
                slc_ = (slice(slc[0].start, datawidget.data.shape[0] - 1, slc[0].step) if slc[0].stop is None
                        else slc[0])
                flat_loc = map_loc(slc_, datawidget.data.fabimage.flatindices())
            else:
                flat_loc = datawidget.data.fabimage.flatindices()
            data_dict['flat_loc'] = flat_loc
        except TypeError: pass
        except AttributeError: pass

        data_dict['theta'] = theta
        data_dict['center'] = center

        return data_dict


    def updateFunctionPartial(self, funcwidget, datawidget, stack_dict=None, slc=None):
        """
        Updates the given FunctionWidget's partial


        Parameters
        ----------
        funcwidget : FunctionWidget
            Widget whos partial is to be updated
        datawidget
            Class holding the input dataset
        stack_dict : dict, optional
            Copy FunctionWidget's param_dict
        slc : slice
            Slice object to extract flat/dark fields when appropriate

        Returns
        -------
        functools.partial
            partial object with updated keywords
        """

        fpartial = funcwidget.partial

        for argname in funcwidget.missing_args: # find a more elegant way to point to the flats and darks
            if argname in 'flats':
                fpartial.keywords[argname] = datawidget.getflats(slc=slc)
            if argname in 'darks':
                fpartial.keywords[argname] = datawidget.getdarks(slc=slc)
            if argname in 'flat_loc': # I don't like this at all
                if slc is not None and slc[0].start is not None:
                    slc_ = (slice(slc[0].start, datawidget.data.shape[0] - 1, slc[0].step) if slc[0].stop is None
                            else slc[0])
                    fpartial.keywords[argname] = map_loc(slc_, datawidget.data.fabimage.flatindices())
                else:
                    fpartial.keywords[argname] = datawidget.data.fabimage.flatindices()

        for param, ipf in funcwidget.input_functions.items():
            args = []
            if not ipf.enabled:
                continue
            if param == 'center':
                if ipf.subfunc_name in FunctionManager.center_func_slc:
                    map(args.append, map(datawidget.data.fabimage.__getitem__,
                                         FunctionManager.center_func_slc[ipf.subfunc_name]))
                else:
                    args.append(datawidget.getsino())

                if ipf.subfunc_name == 'Nelder Mead':
                    ipf.partial.keywords['theta'] = funcwidget.input_functions['theta'].partial()
            fpartial.keywords[param] = ipf.partial(*args)

            if stack_dict and param in stack_dict:  # update the stack dict with new kwargs
                stack_dict[param] = fpartial.keywords[param]


        if funcwidget.func_name in ('Padding', 'Downsample', 'Upsample'):
            self.setCenterCorrection(funcwidget.func_name, fpartial.keywords)
        elif 'Reconstruction' in funcwidget.func_name:
            fpartial.keywords['center'] = self.cor_offset(self.cor_scale(fpartial.keywords['center']))
            self.resetCenterCorrection()

        return fpartial


    def updatePartial(self, function, name, data_dict, param_dict, slc=None):
        """
        Updates the given function partial's keywords - the functools.partial object is the first element of func_tuple

        Parameters
        ----------

        func_tuple : functools.partial
            functools.partial of a function in the processing pipeline
        data_dict : dict
            Dictionary which contains all information relevant to a reconstruction - its elements are loaded into the
            functools.partial's keyword arguments
        param_dict : dict
            Copy of the original keyword arguments of the functools.partial, for reference

        Return
        ------

        function : functools.partial
            Function partial with all keyword arguments loaded
        write : str
            Name of the array function will act on - this allows users to specify which data a function will act on
            in the pipeline
        """

        write = 'tomo'

        for key, val in param_dict.items():
            if isinstance(val, list):
                val = tuple(val)
            if val in data_dict.keys():
                if 'arr' in key or 'tomo' in key:
                    write = val
                function.keywords[key] = data_dict[val]

        if name in ('Padding', 'Downsample', 'Upsample'):
            self.setCenterCorrection(name, function.keywords)
        if 'Reconstruction' in name:
            slc_offset = 0 if (not slc or not slc[2].start) else slc[2].start
            function.keywords['center'] = self.cor_offset(self.cor_scale(function.keywords['center'])) - slc_offset
            self.resetCenterCorrection()
        return function, write

    def loadPreviewData(self, datawidget, slc=None, ncore=None, skip_names=['Write', 'Reader'],
                        fixed_func=None, prange=None):
        """
        Create the function stack and summary dictionary used for running slice previews and 3D previews

        Parameters
        ----------

        datawidget
            Class holding the input dataset
        slc slice
            Slice object to extract tomography/flat/dark data when appropriate
        ncore : int
            number of cores to set the appropriate functions to run on
        skip_names : list of str, optional
            Names of functions to skip when running but still add to the dict representing the pipeline to run.
            Currently only the Writing functions are skipped as writing is not necessary in previews.
        fixed_func : type class
            A dynamic class with only the necessary attributes to be run in a workflow pipeline. This is used for
            parameter range tests to create the class with the parameter to be run and send it to a background thread.
            See testParameterRange for more details

        Returns
        -------
        partial_stack : list of partials:
            List with function partials needed to run preview
        self.stack_dict : dict
            Dictionary summarizing functions and parameters representing the pipeline (used for the list of partials)
        data_dict : dict
            Dictionary of data necessary to run a reconstruction preview
        """

        stack_dict = OrderedDict()
        partial_stack = []
        self.lockParams(True)

        func_pipeline, theta, center, yaml_pipe = self.saveState(datawidget)

        # set up dictionary of function keywords
        params_dict = OrderedDict()
        for tuple in func_pipeline:
            params_dict['{}'.format(tuple[1])] = dict(tuple[0].keywords)

        # load data dictionary
        data_dict = self.loadDataDictionary(datawidget, theta, center, slc = slc)

        count = 1
        for func in self.features:
            name = func.name
            func_name = str(count) + ". " + func.func_name
            if not func.enabled:
                continue
            elif func.func_name in skip_names:
                stack_dict[func_name] = {func.subfunc_name: deepcopy(func.exposed_param_dict)}
                count += 1
                continue
            elif fixed_func is not None and func.func_name == fixed_func.func_name:
                func = fixed_func
                for key, val in func.exposed_param_dict.items():
                    if key in 'center':
                        data_dict[key] = val
                    elif key in params_dict[name].keys() and key not in 'center':
                        params_dict[name][key] = val
            stack_dict[func_name] = {func.subfunc_name: deepcopy(func.exposed_param_dict)}
            count += 1

            # load partial_stack
            fpartial = func.partial
            for arg in inspect.getargspec(func._function)[0]:
                if arg not in fpartial.keywords.keys() or arg in 'center':
                    fpartial.keywords[arg] = '{}'.format(arg)
            # get rid of degenerate keyword arguments
            if 'arr' in fpartial.keywords and 'tomo' in fpartial.keywords:
                fpartial.keywords['tomo'] = fpartial.keywords['arr']
                fpartial.keywords.pop('arr', None)

            # if 'ncore' in fpartial.keywords:
            #     fpartial.keywords['ncore'] = ncore
            partial_stack.append((fpartial, name, params_dict[name]))

            for param, ipf in func.input_functions.items():
                if ipf.enabled:
                    if 'Input Functions' not in stack_dict[func_name][func.subfunc_name]:
                        stack_dict[func_name][func.subfunc_name]['Input Functions'] = {}
                    ipf_dict = {param: {ipf.func_name: {ipf.subfunc_name: ipf.exposed_param_dict}}}
                    stack_dict[func_name][func.subfunc_name]['Input Functions'].update(ipf_dict)

                    # update input function keywords in slice preview table
                    if param in stack_dict[func_name][func.subfunc_name]:
                        stack_dict[func_name][func.subfunc_name][param] = data_dict[param]

        self.lockParams(False)
        return partial_stack, stack_dict, data_dict, prange



    def reconGenerator(self, datawidget, run_state, proj, sino, sino_p_chunk, width, ncore = None):

        """
        Generator for running full reconstruction. Yields messages representing the status of reconstruction
        This is ideally used as a threads.method or the corresponding threads.RunnableIterator.

        Parameters
        ----------
        datawidget : QWidget
            QWidget (usually in the form of a TomoViewer) that holds data
        run_state : list of four elements
            * list of functools.partial which represent the function pipeline
            * array of 'theta' values which represent the angles at which tomography data was taken
            * the center of rotation of the data
            * a string of function names and parameters to be later written into a yaml file
        proj : tuple of int
            Projection range indices (start, end, step)
        sino : tuple of int
            Sinogram range indices (start, end, step)
        sino_p_chunk : int
            Number of sinograms per chunk
        ncore : int
            Number of cores to run functions
        pipeline_dict: dictionary
            Dictionary of parameters referenced during reconstruction

        Yields
        -------
        str
            Message of current status of function
        """

        start_time = time.time()
        write_start = sino[0]
        nchunk = ((sino[1] - sino[0]) // sino[2] - 1) // sino_p_chunk + 1
        total_sino = (sino[1] - sino[0] - 1) // sino[2] + 1
        if total_sino < sino_p_chunk:
            sino_p_chunk = total_sino

        func_pipeline, theta, center, extract = run_state
        yaml_pipe = extract[0]

        # set up dictionary of function keywords
        params_dict = OrderedDict()
        for tuple in func_pipeline:
            params_dict['{}'.format(tuple[1])] = dict(tuple[0].keywords)


        # get save names for pipeline yaml/runnable files
        dir = ""
        for function_tuple in func_pipeline:
            if 'fname' in function_tuple[0].keywords:
                fname = function_tuple[0].keywords['fname']
                for item in fname.split('/')[:-1]:
                    dir += item + '/'
                yml_file = fname + '.yml'
                python_file = fname + '.py'

        # make project directory if it isn't made already
        if not os.path.exists(dir):
            os.makedirs(dir)

        # save function pipeline as runnable
        path = datawidget.path
        runnable = self.extractPipelineRunnable(run_state, params_dict, proj, sino, sino_p_chunk, width, path, ncore)
        try:
            with open(python_file, 'w') as py:
                py.write(runnable)
        except NameError or IOError:
            yield "Error: pipeline python script not written - path could not be found"


        # save yaml in reconstruction folder
        for key in yaml_pipe.keys(): # special case for 'center' param
            if 'Recon' in key:
                for subfunc in yaml_pipe[key].keys():
                    if 'Parameters' in yaml_pipe[key][subfunc].keys():
                        yaml_pipe[key][subfunc]['Parameters']['center'] = float(center)


        try:
            with open(yml_file, 'w') as yml:
                yamlmod.ordered_dump(yaml_pipe, yml)
        except NameError or IOError:
            yield "Error: function pipeline yaml not written - path could not be found"

        for i in range(nchunk):

            start, end  = i * sino[2] * sino_p_chunk + sino[0], (i + 1) * sino[2] * sino_p_chunk + sino[0]
            end = end if end < sino[1] else sino[1]

            slc = (slice(*proj),slice(start, end, sino[2]), slice(*width))


            # load data dictionary
            data_dict = self.loadDataDictionary(datawidget, theta, center, slc = slc)
            data_dict['start'] = write_start
            shape = data_dict['tomo'].shape[1]



            for function_tuple in func_pipeline:
                ts = time.time()
                name = function_tuple[1]
                function = function_tuple[0]

                yield 'Running {0} on slices {1} to {2} from a total of {3} slices...'.format(function_tuple[1],
                                                                                              start, end, total_sino)
                function, write = self.updatePartial(function, name, data_dict, params_dict[name], slc)
                data_dict[write] = function()

                yield ' Finished in {:.3f} s\n'.format(time.time() - ts)

            write_start += shape
            del data_dict


        # print final 'finished with recon' message
        yield 'Reconstruction complete. Run time: {:.2f} s'.format(time.time() - start_time)



    def foldSliceStack(self, partial_stack, data_dict):
        """
        Method to run a reconstruction given a list of function partials and the data for functions to act on

        Parameters
        ----------
         partial_stack : list of 3-tuples
            Contains: a list of tuples, each of which have as elements: functools.partial of full keywords to run,
            the name of the associated function, and a copy of the params belonging to that function
        data_dict : dict
            Dictionary containing all data needed to run a reconstruction

        Returns
        -------
        Returns the 'tomo' data in the data_dict, which has been acted on by all functions in the partial_stack
        """
        for tuple in partial_stack:
            function, write = self.updatePartial(tuple[0], tuple[1], data_dict, tuple[2])
            data_dict[write] = function()


        return data_dict['tomo']


    @staticmethod
    def foldFunctionStack(partial_stack, initializer):
        """
        Static class method to fold a partial function stack given an initializer

        Parameters
        ----------
        partial_stack : list of functools.partial
            List of partials that require only the input array to run.
        initializer : ndarray
            Array to use as initializer for folding operation

        Returns
        -------
        Return value of last partial in stack
            Result of folding operation
        """

        return reduce(lambda f1, f2: f2(f1), partial_stack, initializer)


    def previewFunctionStack(self, datawidget, slc=None, ncore=None, skip_names=['Write'], fixed_func=None):

        """
        Create the function stack and summary dictionary used for running slice previews and 3D previews

        Deprecated : functionality replaced by self.loadPreviewData


        Parameters
        ----------
        datawidget
            Class holding the input dataset
        slc slice
            Slice object to extract tomography/flat/dark data when appropriate
        ncore : int
            number of cores to set the appropriate functions to run on
        skip_names : list of str, optional
            Names of functions to skip when running but still add to the dict representing the pipeline to run.
            Currently only the Writing functions are skipped as writing is not necessary in previews.
        fixed_func : type class
            A dynamic class with only the necessary attributes to be run in a workflow pipeline. This is used for
            parameter range tests to create the class with the parameter to be run and send it to a background thread.
            See testParameterRange for more details

        Returns
        -------
        list of partials:
            List with function partials needed to run preview
        dict
            Dictionary summarizing functions and parameters representing the pipeline (used for the list of partials)
        """

        self.stack_dict = OrderedDict()
        partial_stack = []
        self.lockParams(True)


        for func in self.features:
            if not func.enabled:
                continue
            elif func.func_name in skip_names:
                self.stack_dict[func.func_name] = {func.subfunc_name: deepcopy(func.exposed_param_dict)}
                continue
            elif fixed_func is not None and func.func_name == fixed_func.func_name:
                func = fixed_func  # replace the function with the fixed function
            self.stack_dict[func.func_name] = {func.subfunc_name: deepcopy(func.exposed_param_dict)}
            p = self.updateFunctionPartial(func, datawidget, self.stack_dict[func.func_name][func.subfunc_name], slc)
            if 'ncore' in p.keywords:
                p.keywords['ncore'] = ncore
            partial_stack.append(p)
            for param, ipf in func.input_functions.items():
                if ipf.enabled:
                    if 'Input Functions' not in self.stack_dict[func.func_name][func.subfunc_name]:
                        self.stack_dict[func.func_name][func.subfunc_name]['Input Functions'] = {}
                    ipf_dict = {param: {ipf.func_name: {ipf.subfunc_name: ipf.exposed_param_dict}}}
                    self.stack_dict[func.func_name][func.subfunc_name]['Input Functions'].update(ipf_dict)

        self.lockParams(False)
        return partial_stack, self.stack_dict


    def functionStackGenerator(self, datawidget, pipeline_dict, proj, sino, sino_p_chunk, ncore=None):
        """
        Generator for running full reconstruction. Yields messages representing the status of reconstruction
        This is ideally used as a threads.method or the corresponding threads.RunnableIterator.

        Deprecated : functionality replaced by self.reconGenerator


        Parameters
        ----------
        datawidget
        proj : tuple of int
            Projection range indices (start, end, step)
        sino : tuple of int
            Sinogram range indices (start, end, step)
        sino_p_chunk : int
            Number of sinograms per chunk
        ncore : int
            Number of cores to run functions
        pipeline_dict: dictionary
            Dictionary of parameters referenced during reconstruction

        Yields
        -------
        str
            Message of current status of function
        """

        start_time = time.time()
        write_start = sino[0]
        nchunk = ((sino[1] - sino[0]) // sino[2] - 1) // sino_p_chunk + 1
        total_sino = (sino[1] - sino[0] - 1) // sino[2] + 1
        if total_sino < sino_p_chunk:
            sino_p_chunk = total_sino


        for i in range(nchunk):
            init = True
            start, end = i * sino[2] * sino_p_chunk + sino[0], (i + 1) * sino[2] * sino_p_chunk + sino[0]
            end = end if end < sino[1] else sino[1]



            for function in self.features:
                # if not function.enabled:
                if not pipeline_dict[function.name]['enabled']:
                    continue
                ts = time.time()
                yield 'Running {0} on slices {1} to {2} from a total of {3} slices...'.format(function.name, start,
                                                                                              end, total_sino)

                fpartial = self.updateFunctionPartial(function, datawidget, pipeline_dict,
                                                      slc=(slice(*proj), slice(start, end, sino[2]),
                                                           slice(None, None, None)))
                if init:
                    tomo = datawidget.getsino(slc=(slice(*proj), slice(start, end, sino[2]),
                                                   slice(None, None, None)))
                    init = False
                elif 'Tiff' in function.name:
                    fpartial.keywords.pop('parent folder', None)
                    fpartial.keywords.pop('folder name', None)
                    fpartial.keywords.pop('file name', None)
                    fpartial.keywords['start'] = write_start
                    write_start += tomo.shape[0]
                # elif 'Reconstruction' in fname:
                #     # Reset input_partials to None so that centers and angle vectors are not computed in every iteration
                #     # and set the reconstruction partial to the updated one.
                #     if ipartials is not None:
                #         ind = next((i for i, names in enumerate(fpartials) if fname in names), None)
                #         fpartials[ind][0], fpartials[ind][4] = fpartial, None
                #     tomo = fpartial(tomo)
                tomo = fpartial(tomo)
                yield ' Finished in {:.3f} s\n'.format(time.time() - ts)

        # save yaml in reconstruction folder
        for key in pipeline_dict.keys():
            if 'Write' in key:
                save_file = pipeline_dict[key]['fname'] + '.yml'
        try:
            with open(save_file, 'w') as yml:
                yamlmod.ordered_dump(pipeline_dict['pipeline_for_yaml'], yml)
        except NameError:
            yield "Error: function pipeline yaml not written - path could not be found"

        # print final 'finished with recon' message
        yield 'Reconstruction complete. Run time: {:.2f} s'.format(time.time()-start_time)


    def testParameterRange(self, function, parameter, prange):
        """
        Used to set off parameter range tests. Emits sigTestRange with message and a fixed_func object representing the
        function who's parameter is to be changed

        Parameters
        ----------
        function : FunctionWidget
            Widget containing the parameter to be evaluated
        parameter : str
            Parameter name
        prange : tuple/list
            Range of parameters to be evaluated
        """
        self.updateParameters()
        if function.func_name in 'Reader':
            return
        for i in prange:
            function.param_dict[parameter] = i
            # Dynamic FixedFunc "dummed down" FuncWidget class. cool.
            fixed_func = type('FixedFunc', (), {'func_name': function.func_name, 'subfunc_name': function.subfunc_name,
                                                'missing_args': function.missing_args,
                                                'param_dict': function.param_dict,
                                                'exposed_param_dict': function.exposed_param_dict,
                                                'partial': function.partial,
                                                'input_functions': function.input_functions,
                                                '_function': function._function})
            self.sigTestRange.emit('Computing preview for {} parameter {}={}...'.format(function.name, parameter, i),
                                   fixed_func, {'function': function.func_name, parameter: prange})



    def setPipelineFromYAML(self, pipeline, setdefaults=False, config_dict=config.names):
        """
        Sets the managers function/feature list from a dictionary from a YAML file.

        Parameters
        ----------
        pipeline : dict
            Dict extracted from YAML file
        setdefaults : bool
            Set the given parameter values as defaults
        config_dict : dict, optional
            Dictionary with configuration specifications/function parameter details
        """

        self.removeAllFeatures()
        # Way too many for loops, oops... may want to restructure the yaml files
        for func, subfuncs in pipeline.items():
            try:
                func = func.split(". ")[1]
            except IndexError:
                func = func
            for subfunc in subfuncs:
                funcWidget = self.addFunction(func, subfunc, package=reconpkg.packages[config_dict[subfunc][1]])
                if 'Enabled' in subfuncs[subfunc] and not subfuncs[subfunc]['Enabled']:
                    funcWidget.enabled = False
                if 'Parameters' in subfuncs[subfunc]:
                    for param, value in subfuncs[subfunc]['Parameters'].items():
                        child = funcWidget.params.child(param)
                        child.setValue(value)
                        if setdefaults:
                            child.setDefault(value)
                if 'Input Functions' in subfuncs[subfunc]:
                    for param, ipfs in subfuncs[subfunc]['Input Functions'].items():
                        for ipf, sipfs in ipfs.items():
                            for sipf in sipfs:
                                if param in funcWidget.input_functions:
                                    ifwidget = funcWidget.input_functions[param]
                                else:
                                    ifwidget = self.addInputFunction(funcWidget, param, ipf, sipf,
                                                                     package=reconpkg.packages[config_dict[sipf][1]])
                                if 'Enabled' in sipfs[sipf] and not sipfs[sipf]['Enabled']:
                                    ifwidget.enabled = False
                                if 'Parameters' in sipfs[sipf]:
                                    for p, v in sipfs[sipf]['Parameters'].items():
                                        ifwidget.params.child(p).setValue(v)
                                        if setdefaults:
                                            ifwidget.params.child(p).setDefault(v)
                                ifwidget.updateParamsDict()
                funcWidget.updateParamsDict()
        self.sigPipelineChanged.emit()

    def setPipelineFromDict(self, pipeline, config_dict=config.names):
        """
        Sets the managers function/feature list from a dictionary extracted from a summary dictionary as the ones
        displayed in previews

        Parameters
        ----------
        pipeline : dict
            Dict representing the workflow pipeline
        config_dict : dict, optional
            Dictionary with configuration specifications/function parameter details
        """

        self.removeAllFeatures()
        for func, subfuncs in pipeline.items():
            try:
                func = func.split(". ")[1]
            except IndexError:
                func = func
            for subfunc in subfuncs:
                funcWidget = self.addFunction(func, subfunc, package=reconpkg.packages[config_dict[subfunc][1]])
                for param, value in subfuncs[subfunc].items():
                    if param == 'Package':
                        continue
                    elif param == 'Input Functions':
                        for param, ipfs in value.items():
                            for ipf, sipf in ipfs.items():
                                ifwidget = self.addInputFunction(funcWidget, param, ipf, sipf.keys()[0],
                                                    package=reconpkg.packages[config_dict[sipf.keys()[0]][1]])
                                for p, v in sipf[sipf.keys()[0]].items():
                                    ifwidget.params.child(p).setValue(v)
                                ifwidget.updateParamsDict()
                    else:
                        funcWidget.params.child(param).setValue(value)
                    funcWidget.updateParamsDict()
        self.sigPipelineChanged.emit()

    def extractPipelineRunnable(self, run_state, params, proj, sino, sino_p_chunk, width, path, ncore=None):
        """
        Saves the function pipeline as a runnable (Python) file.

        Parameters
        ----------
        pipeline : dict
            Dictionary of functions and their necessary parameters to write the function information
        """


        signature = "import time \nimport tomopy \nimport dxchange\nimport h5py\n" \
                    "import numpy as np\nimport numexpr as ne\n\n"

        # set up function pipeline
        runnable_pipe = run_state[3][1]
        func_dict = runnable_pipe['func']
        subfunc_dict = runnable_pipe['subfunc']
        center = run_state[2]

        signature += "def main():\n\n"
        signature += "\t# offset and scale factors in case of padding, upsampling, or downsampling\n"
        signature += "\tcor_offset = 0\n"
        signature += "\tcor_scale = 0\n\n"
        signature += "\tstart_time = time.time()\n\n"

        signature += "\n\tdata = dxchange.read_als_832h5('{}')\n".format(path)
        signature += "\ttomo=data[0]; flats=data[1]; dark=data[2]\n"
        signature += "\tmdata = read_als_832h5_metadata('{}')\n\n".format(path)
        signature += "\t# choose which projections and sinograms go into the reconstruction:\n"
        signature += "\tproj_start = {}; proj_end = {}; proj_step = {}\n".format(proj[0],proj[1],proj[2])
        signature += "\tsino_start = {}; sino_end = {}; sino_step = {}\n".format(sino[0],sino[1],sino[2])
        signature += "\twidth_start = {}; width_end = {}; width_step = 1\n".format(width[0], width[1])
        signature += "\tsino_p_chunk = {2} # chunk size of data during reconstruction\n\n".format(proj, sino, sino_p_chunk)
        signature += "\tproj = (proj_start, proj_end, proj_step)\n"
        signature += "\tsino = (sino_start, sino_end, sino_step)\n"
        signature += "\twidth = (width_start, width_end, width_step)\n\n"
        signature += "\twrite_start = sino[0]\n"
        signature += "\tnchunk = ((sino[1]-sino[0]) // sino[2] - 1) // sino_p_chunk +1\n"
        signature += "\ttotal_sino = (sino[1] - sino[0] - 1) // sino[2] + 1\n"
        signature += "\tif total_sino < sino_p_chunk:\n\t\tsino_p_chunk = total_sino\n\n"

        if 'center' not in subfunc_dict.items():
            signature += "\tcenter = {}\n".format(center)
        for key, val in subfunc_dict.items():
            signature += "\t{} = {}\n".format(key, val)

        signature += "\n\n\t# MAIN LOOP FOR RECONSTRUCTION\n"
        signature += "\tfor i in range(nchunk):\n"
        signature += "\t\tstart, end = i * sino[2] * sino_p_chunk + sino[0], (i + 1) * sino[2] * sino_p_chunk + sino[0]\n"
        signature += "\t\tend = end if end < sino[1] else sino[1]\n\n"
        signature += "\t\tslc = (slice(*proj), slice(start,end,sino[2]), slice(*width))\n"

        signature += "\t\tdata_dict = loadDataDict(data, mdata, theta, center, slc)\n"
        signature += "\t\tdata_dict['start'] = write_start\n"
        signature += "\t\tshape = data_dict['tomo'].shape[1]\n\n"

        signature += "\t\t# the function pipeline: keywords used in each function are located in the\n"
        signature += "\t\t# 'params' assignment for each function\n\n"
        for func, param_dict in func_dict.items():
            try:
                func = func.split(". ")[1]
            except IndexError:
                pass
            signature += "\t\t# function: {}\n".format(func)
            signature += "\t\tts = time.time()\n"
            signature += "\t\tprint 'Running {0} on slices {1} to {2} from a total of {3} slices'.format("
            signature += "'{}', start, end, total_sino)\n ".format('{}'.format(func))
            signature += "\t\tparams = {}\n".format(param_dict)
            signature += "\t\tkwargs, write, cor_offset, cor_scale = updateKeywords('{}', params, data_dict,".format(func)
            signature += " cor_offset, cor_scale, width)\n"
            signature += "\t\tdata_dict[write] = {}(**kwargs)\n".format(func)
            signature += "\t\tprint 'Finished in {:.3f} s'.format(time.time()-ts)\n"
            signature += "\t\tprint "" #white space \n\n"
        signature += "\t\twrite_start += shape\n\n"
        signature += "\tprint 'Reconstruction complete. Run time: {:.2f} s'.format(time.time()-start_time)\n"
        signature += "\tprint # white space\n\n"

        # rewrite functions used for processing
        signature += "# helper functions\n\n"
        signature += "def read_als_832h5_metadata(fname):\n"
        signature += "\t with h5py.File(fname, 'r') as f:\n\t\tg=_find_dataset_group(f)\n\t\treturn dict(g.attrs)\n\n"

        signature += "def _find_dataset_group(h5object):\n"
        signature += "\tkeys = h5object.keys()\n \tif len(keys)==1:\n"
        signature += "\t\tif isinstance(h5object[keys[0]], h5py.Group):\n"
        signature += "\t\t\tgroup_keys = h5object[keys[0]].keys()\n"
        signature += "\t\t\tif isinstance(h5object[keys[0]][group_keys[0]], h5py.Dataset):\n"
        signature += "\t\t\t\treturn h5object[keys[0]]\n"
        signature += "\t\t\telse:\n\t\t\t\treturn _find_dataset_group(h5object[keys[0]])\n"
        signature += "\t\telse:\n\t\t\traise Exception('Unable to find dataset group')\n"
        signature += "\telse:\n\t\traise Exception('Unable to find dataset group')\n\n"

        signature += "def flatindices(mdata):\n"
        signature += "\ti0 = int(mdata['i0cycle'])\n\tnproj = int(mdata['nangles'])\n"
        signature += "\tif i0 > 0:\n\t\tindices = list(range(0, nproj, i0))\n"
        signature += "\t\tif indices[-1] != nproj - 1:\n\t\t\tindices.append(nproj - 1)\n"
        signature += "\telif i0 == 0:\n\t\tindices = [0, nproj - 1]\n\treturn indices\n\n"

        signature += "# sets COR correction in case of padding, upsample, or downsample\n"
        signature += "def setCenterCorrection(name, param_dict, cor_offset, cor_scale):\n"
        signature += "\tif 'pad' in name and param_dict['axis'] == 2:\n"
        signature += "\t\tn = param_dict['npad']\n"
        signature += "\t\tcor_offset = n\n"
        signature += "\telif 'downsample' in name and param_dict['axis'] == 2:\n"
        signature += "\t\ts = param_dict['level']\n"
        signature += "\t\tcor_scale = -s\n"
        signature += "\telif 'upsample' in name and param_dict['axis'] == 2:\n"
        signature += "\t\ts = param_dict['level']\n"
        signature += "\t\tcor_scale = -s\n"
        signature += "\treturn cor_offset, cor_scale\n\n"
        signature += "def resetCenterCorrection(cor_offset, cor_scale):\n"
        signature += "\tcor_offset = 0\n\tcor_scale = 0\n"
        signature += "\treturn cor_offset, cor_scale\n\n"

        signature += "# performs COR correction\n"
        signature += "def correctCenter(center, cor_offset, cor_scale, width):\n"
        signature += "\tif cor_scale<0:\n\t\treturn float(int(center * 2 ** cor_scale)) + cor_offset - width[0]\n"
        signature += "\telse:\n\t\treturn (center * 2 ** cor_scale) + cor_offset - width[0]\n\n"


        signature += "def map_loc(slc,loc):\n\tstep = slc.step if slc.step is not None else 1\n"
        signature += "\tind = range(slc.start, slc.stop, step)\n\tloc = np.array(loc)\n\tlow, upp = ind[0], ind[-1]\n"
        signature += "\tbuff = (loc[-1] - loc[0]) / len(loc)\n\tmin_loc = low - buff\n\tmax_loc = upp + buff\n"
        signature += "\tloc = np.intersect1d(loc[loc > min_loc], loc[loc < max_loc])\n\tnew_upp = len(ind)\n"
        signature += "\tloc = (new_upp * (loc - low)) // (upp - low)\n\tif loc[0] < 0:\n\t\tloc[0] = 0\n"
        signature += "\treturn np.ndarray.tolist(loc)\n\n"

        # function for loading data dictionary
        signature += "def loadDataDict(data, mdata, theta,center,slc=None):\n\tdata_dict = {}\n"
        signature += "\tif slc is not None and slc[0].start is not None:\n"
        signature += "\t\tslc_ = slice(slc[0].start,data[0].shape[0],slc[0].step)\n"
        signature += "\t\tflat_loc = map_loc(slc_, flatindices(mdata))\n"
        signature += "\telse:\n\t\tflat_loc = flatindices(mdata)\n\n"
        signature += "\tdata_dict['tomo'] = data[0][slc]\n\tdata_dict['flats'] = data[1][slc]\n"
        signature += "\tdata_dict['dark'] = data[2][slc]\n\tdata_dict['flat_loc'] = flat_loc\n"
        signature += "\tdata_dict['theta'] = theta\n\tdata_dict['center'] = center\n\n"
        signature += "\treturn data_dict\n\n"

        signature += "def updateKeywords(function, param_dict, data_dict, cor_offset, cor_scale, width):\n"
        signature += "\twrite = 'tomo'\n"
        signature += "\tfor key, val in param_dict.iteritems():\n"
        signature += "\t\tif val in data_dict.iterkeys():\n"
        signature += "\t\t\tif 'arr' in key or 'tomo' in key:\n"
        signature += "\t\t\t\twrite = val\n"
        signature += "\t\t\tparam_dict[key] = data_dict[val]\n"
        signature += "\tfor item in ('pad', 'downsample', 'upsample'):\n"
        signature += "\t\tif item in function:\n "
        signature += "\t\t\tcor_offset, cor_scale = setCenterCorrection(function, param_dict, cor_offset, cor_scale)\n"
        signature += "\tif 'recon' in function:\n"
        signature += "\t\tparam_dict['center'] = correctCenter(param_dict['center'], cor_offset, cor_scale, width)\n"
        signature += "\t\tcor_offset, cor_scale = resetCenterCorrection(cor_offset, cor_scale)\n"
        signature += "\treturn param_dict, write, cor_offset, cor_scale\n\n\n"

        # write custom functions as functions in python file
        signature += "# the following three functions may be used in the reconstruction pipeline\n"
        signature += "def crop(arr, p11, p12, p21, p22, axis=0):\n"
        signature += "\tslc = []\n"
        signature += "\tpts = [p11, p12, p21, p22]\n"
        signature += "\tfor n in range(len(arr.shape)):\n"
        signature += "\t\tif n == axis:\n"
        signature += "\t\t\tslc.append(slice(None))\n"
        signature += "\t\telse:\n"
        signature += "\t\t\tslc.append(slice(pts.pop(0), -pts.pop(0)))\n"
        signature += "\treturn arr[slc]\n\n"

        signature += "def convert_data(arr, imin=None, imax=None, dtype='uint8', intcast='float32'):\n"
        signature += "\tDTYPE_RANGE = {'uint8': (0, 255), 'uint16': (0, 65535), 'int8': (-128, 127),"
        signature += "'int16': (-32768, 32767),'float32': (-1, 1),'float64': (-1, 1)}\n"
        signature += "\tallowed_dtypes = ('uint8', 'uint16', 'int8', 'int16', 'float32', 'float64')\n"
        signature += "\tif dtype not in allowed_dtypes:\n"
        signature += "\t\traise ValueError('dtype keyword {0} not in allowed keywords {1}'.format(dtype, allowed_dtypes))\n\n"

        signature += "\t# Determine range to cast values\n"
        signature += "\tminset = False\n"
        signature += "\tif imin is None:\n"
        signature += "\t\timin = np.min(arr)\n"
        signature += "\t\tminset = True\n"
        signature += "\tmaxset = False\n"
        signature += " \tif imax is None:\n"
        signature += "\t\timax = np.max(arr)\n"
        signature += "\t\tmaxset = True\n\n"

        signature += "\tnp_cast = getattr(np, str(arr.dtype))\n"
        signature += "\timin, imax = np_cast(imin), np_cast(imax)\n"

        signature += "\t# Determine range of new dtype\n"
        signature += "\tomin, omax = DTYPE_RANGE[dtype]\n"
        signature += "\tomin = 0 if imin >= 0 else omin\n"
        signature += "\tomin, omax = np_cast(omin), np_cast(omax)\n"

        signature += "\tif arr.dtype in [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16,"
        signature += "np.uint32, np.uint64, np.bool_, np.int_, np.intc, np.intp]:\n"
        signature += "\t\tint_cast = getattr(np, str(intcast))\n"
        signature += "\t\tout = np.empty(arr.shape, dtype=int_cast)\n"
        signature += "\t\timin = int_cast(imin)\n"
        signature += "\t\timax = int_cast(imax)\n"
        signature += "\t\tdf = int_cast(imax) - int_cast(imin)\n"
        signature += "\telse:\n"
        signature += "\t\tout = np.empty(arr.shape, dtype=arr.dtype)\n"
        signature += "\t\tdf = imax - imin\n"
        signature += "\tif not minset:\n"
        signature += "\t\tif np.min(arr) < imin:\n"
        signature += "\t\t\tarr = ne.evaluate('where(arr < imin, imin, arr)', out=out)\n"
        signature += "\tif not maxset:\n"
        signature += "\t\tif np.max(arr) > imax:\n"
        signature += "\t\t\tarr = ne.evaluate('where(arr > imax, imax, arr)', out=out)\n"
        signature += "\tne.evaluate('(arr - imin) / df', truediv=True, out=out)\n"
        signature += "\tne.evaluate('out * (omax - omin) + omin', out=out)\n\n"

        signature += "\t# Cast data to specified type\n"
        signature += "\treturn out.astype(np.dtype(dtype), copy=False)\n\n"

        signature += """
def array_operation_add(arr, value=0):
    return ne.evaluate('arr + value')

def array_operation_sub(arr, value=0):
    return ne.evaluate('arr - value', truediv=True)

def array_operation_mult(arr, value=1):
    return ne.evaluate('arr * value')

def array_operation_div(arr, value=1):
    return ne.evaluate('arr / value')

def array_operation_max(arr, value=0):
    return np.maximum(arr, value)"""

        signature += "\n\nif __name__ == '__main__':\n\tmain()"

        return signature



def map_loc(slc, loc):
    """
    Does a linear mapping of the indices in loc from a range given by slc start and stop with step of one to a new
    range given by len(range(slc.start, slc.stop, slc.step))

    Parameters
    ----------
    slc : slice
    loc : list
        list of indices assumed to span from slc.start to slc.stop

    Returns
    -------
    list
        mapped indices to new range

    """

    step = slc.step if slc.step is not None else 1
    ind = range(slc.start, slc.stop, step)
    loc = np.array(loc)
    low, upp = ind[0], ind[-1]
    buff = (loc[-1] - loc[0]) / len(loc)
    min_loc = low - buff
    max_loc = upp + buff
    loc = np.intersect1d(loc[loc > min_loc], loc[loc < max_loc])
    new_upp = len(ind)
    loc = (new_upp * (loc - low)) // (upp - low)
    if loc[0] < 0:
        loc[0] = 0

    return np.ndarray.tolist(loc)

class CORSelectionWidget(QtGui.QWidget):

    cor_detection_funcs = ['Phase Correlation', 'Vo', 'Nelder-Mead']
    sigCORFuncChanged = QtCore.Signal(str, QtGui.QWidget)

    def __init__(self, subname='Phase Correlation', parent=None):
        super(CORSelectionWidget, self).__init__(parent=parent)

        self.layout = QtGui.QVBoxLayout()
        self.function = fc.FunctionWidget(name="Center Detection", subname=subname,
                                package=reconpkg.packages[config.names[subname][1]])
        self.params = pg.parametertree.Parameter.create(name=self.function.name,
                                             children=config.parameters[self.function.subfunc_name], type='group')

        self.param_tree = pg.parametertree.ParameterTree()
        self.param_tree.setMinimumHeight(200)
        self.param_tree.setMinimumWidth(200)
        self.param_tree.setParameters(self.params, showTop=False)
        for key, val in self.function.param_dict.items():
            if key in [p.name() for p in self.params.children()]:
                self.params.child(key).setValue(val)
                self.params.child(key).setDefault(val)

        self.method_box = QtGui.QComboBox()
        self.method_box.currentIndexChanged.connect(self.changeFunction)
        for item in self.cor_detection_funcs:
            self.method_box.addItem(item)
        self.method_box.currentIndexChanged.connect(self.corFuncChanged)

        label = QtGui.QLabel('COR detection function: ')
        method_layout = QtGui.QHBoxLayout()
        method_layout.addWidget(label)
        method_layout.addWidget(self.method_box)

        self.layout.addLayout(method_layout)
        self.layout.addWidget(self.param_tree)
        self.setLayout(self.layout)

    def corFuncChanged(self, index):
        self.sigCORFuncChanged.emit(self.cor_detection_funcs[index], self)

    def changeFunction(self, index):
        subname = self.method_box.itemText(index)
        self.layout.removeWidget(self.param_tree)

        self.function = fc.FunctionWidget(name="Center Detection", subname=subname,
                                package=reconpkg.packages[config.names[subname][1]])
        self.params = pg.parametertree.Parameter.create(name=self.function.name,
                                             children=config.parameters[self.function.subfunc_name], type='group')
        self.param_tree = pg.parametertree.ParameterTree()
        self.param_tree.setMinimumHeight(200)
        self.param_tree.setMinimumWidth(200)
        self.param_tree.setParameters(self.params,showTop = False)
        for key, val in self.function.param_dict.items():
            if key in [p.name() for p in self.params.children()]:
                self.params.child(key).setValue(val)
                self.params.child(key).setDefault(val)

        self.layout.addWidget(self.param_tree)
        self.setLayout(self.layout)






















