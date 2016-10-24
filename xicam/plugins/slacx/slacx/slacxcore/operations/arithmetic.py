import numpy as np

from slacxop import Operation


class Add(Operation):
    """Add two objects."""

    def __init__(self):
        input_names = ['augend', 'addend']
        output_names = ['sum']
        super(Add, self).__init__(input_names, output_names)
        self.input_doc['augend'] = 'array or number'
        self.input_doc['addend'] = 'array or number for which addition with augend is defined'
        self.output_doc['sum'] = 'augend plus addend'
        self.categories = ['ARITHMETIC']

    def run(self):
        self.outputs['sum'] = self.inputs['augend'] + self.inputs['addend']


class Multiply(Operation):
    """Multiply two objects."""

    def __init__(self):
        input_names = ['multiplicand', 'multiplier']
        output_names = ['product']
        super(Multiply, self).__init__(input_names, output_names)
        self.input_doc['multiplicand'] = 'array or number'
        self.input_doc['multiplier'] = 'array or number for which multiplication with multiplicand is defined'
        self.output_doc['product'] = 'multiplicand times multiplier'
        self.categories = ['ARITHMETIC']

    def run(self):
        print self.inputs
        print self.inputs['multiplicand']
        print self.inputs['multiplier']
        self.outputs['product'] = self.inputs['multiplicand'] * self.inputs['multiplier']


class Subtract(Operation):
    """Subtract one object from another."""

    def __init__(self):
        input_names = ['minuend', 'subtrahend']
        output_names = ['difference']
        super(Subtract, self).__init__(input_names, output_names)
        self.input_doc['minuend'] = 'array or number'
        self.input_doc['subtrahend'] = 'array or number for which subtraction from minuend is defined'
        self.output_doc['difference'] = 'minuend minus subtrahend'
        self.categories = ['ARITHMETIC']

    def run(self):
        self.outputs['difference'] = self.inputs['minuend'] - self.inputs['subtrahend']


class Divide(Operation):
    """Divide two objects."""

    def __init__(self):
        input_names = ['dividend', 'divisor']
        output_names = ['quotient']
        super(Divide, self).__init__(input_names, output_names)
        self.input_doc['dividend'] = 'array or number'
        self.input_doc['divisor'] = 'array or number for which dividing dividend is defined'
        self.output_doc['quotient'] = 'dividend divided by divisor'
        self.categories = ['ARITHMETIC']

    def run(self):
        self.outputs['quotient'] = self.inputs['dividend'] / self.inputs['divisor']


class Exponentiate(Operation):
    """Exponentiate an object by another object."""

    def __init__(self):
        input_names = ['base', 'exponent']
        output_names = ['power']
        super(Exponentiate, self).__init__(input_names, output_names)
        self.input_doc['base'] = 'array or number'
        self.input_doc['exponent'] = 'array or number for which exponentiating base is defined'
        self.output_doc['power'] = 'base raised by exponent'
        self.categories = ['ARITHMETIC']

    def run(self):
        self.outputs['power'] = self.inputs['base'] ** self.inputs['exponent']


#  Testing 1 2 3

class Logarithm(Operation):
    """Take the logarithm of an object by some base."""

    def __init__(self):
        input_names = ['power', 'base']
        output_names = ['exponent']
        super(Logarithm, self).__init__(input_names, output_names)
        self.input_doc['power'] = 'array or number whose logarithm will be taken'
        self.input_doc['base'] = 'array or number'
        self.output_doc['exponent'] = 'array or number'
        self.categories = ['ARITHMETIC']

    def run(self):
        self.outputs['exponent'] = np.log(self.inputs['power'])/np.log(self.inputs['base'])
