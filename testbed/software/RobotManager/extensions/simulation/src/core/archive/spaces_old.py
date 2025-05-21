import copy as cp
import numpy as np

import scioi_py_core.utils.utils as utils
import scioi_py_core.utils.orientations as orientation_utils


class Dimension:
    """

    """
    name: str  # Name of the dimension, such as "x" or "y"
    unit: str  # Name of the unit
    limits: list  # Upper and lower limit
    wrapping: bool  # If wrapping is true, then the dimension will wrap around the upper or lower limit
    discretization: float  # lowest increment of the value of the dimension
    error_on_limit: bool  # If TRUE an error will be generated if the value violates the limits
    complex: bool  # If TRUE, it allows for complex numbers
    datatype: type
    value_type: type

    def __init__(self, name, discretization=0, limits=None, wrapping=False, unit=None, error_on_limit=False,
                 complex=False, datatype: type = float):
        self.name = name
        self.discretization = discretization
        self.limits = limits
        self.wrapping = wrapping
        self.unit = unit
        self.error_on_limit = error_on_limit

        self.complex = complex
        self.datatype = datatype

    # == METHODS =======================================================================================================
    def project(self, value):

        if value is None:
            return None

        value = float(value)

        if self.limits is not None:
            if self.wrapping:
                value = utils.wrap(self.limits, value)
            else:
                if not utils.inInterval(self.limits, value):
                    if self.error_on_limit:
                        raise Exception("Value violates dimension constraints")
                    else:
                        value = utils.stickToInterval(self.limits, value)

        if self.discretization > 0:
            value = self.discretization * round(value / self.discretization)

        return value

    # ------------------------------------------------------------------------------------------------------------------
    def zero(self):
        return 0.0

    # ------------------------------------------------------------------------------------------------------------------
    def none(self):
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def __repr__(self):
        return f"{self.name}"


class VectorDimension(Dimension):
    shape: tuple
    dimensions: list
    len: int
    dim_names: list

    def __init__(self, name, shape: tuple, names: list = None, limits: list = None, wrapping: (list, bool) = None,
                 discretization: list = None):
        super().__init__(name)

        assert (isinstance(shape, tuple) and len(shape) == 1)
        self.len = shape[0]
        self.shape = shape

        self.dimensions = []
        self.dim_names = []
        for i in range(0, self.len):
            if names is not None:
                dim_name = names[i]
            else:
                dim_name = f"dim_{i}"

            self.dim_names.append(dim_name)

            if limits is not None:
                dim_limits = limits[i]
            else:
                dim_limits = None

            if wrapping is not None:
                if isinstance(wrapping, list):
                    dim_wrapping = wrapping[i]
                elif isinstance(wrapping, bool):
                    dim_wrapping = wrapping
                else:
                    dim_wrapping = False
            else:
                dim_wrapping = False

            if discretization is not None:
                dim_discretization = discretization[i]
            else:
                dim_discretization = 0

            self.dimensions.append(Dimension(name=dim_name, limits=dim_limits, wrapping=dim_wrapping,
                                             discretization=dim_discretization))

    # ------------------------------------------------------------------------------------------------------------------
    def project(self, value, index=None):

        if value is None:
            return None

        if isinstance(value, list):
            assert (len(value) == len(self.dimensions))
        elif isinstance(value, np.ndarray):
            assert (np.shape(value) == (len(self.dimensions),))
        elif isinstance(value, (int, float)):
            assert (index is not None and isinstance(index, int) and index < self.len)

        if isinstance(value, (list, np.ndarray)):
            new_value = np.ndarray(shape=self.shape)
            for i, dim in enumerate(self.dimensions):
                new_value[i] = dim.project(value[i])
            return new_value
        elif index is not None:
            return self.dimensions[index].project(value)

    # ------------------------------------------------------------------------------------------------------------------
    def zero(self):
        return np.zeros(shape=self.shape)

    def none(self):
        return None


class MatrixDimension(Dimension):
    shape: tuple

    def __init__(self, name, shape: tuple):
        super().__init__(name)
        self.shape = shape

    def project(self, value):
        if isinstance(value, list):
            new_val = np.asarray(value)
            if new_val.shape == self.shape:
                return new_val
            else:
                raise Exception
        elif isinstance(value, np.ndarray):
            if value.shape == self.shape:
                return value

    def zero(self):
        return np.zeros(self.shape)

    def none(self):
        return None


# ======================================================================================================================
class StateValue:
    dim: 'Dimension'
    value: object

    def __init__(self):
        ...

    def none(self):
        pass

    def zero(self):
        pass

    def one(self):
        pass

    def set(self, value, index=None):
        pass


class ScalarValue(StateValue):
    dim: Dimension
    value: float

    def __init__(self, dim, value: float = None):
        super().__init__()
        self.dim = dim
        self.value = self.dim.project(value)

    # ------------------------------------------------------------------------------------------------------------------
    def set(self, value):
        self.value = self.dim.project(value)

    # ------------------------------------------------------------------------------------------------------------------
    def none(self):
        self.value = self.dim.none()

    # ------------------------------------------------------------------------------------------------------------------
    def one(self):
        self.value = self.dim.project(1)

    # ------------------------------------------------------------------------------------------------------------------
    def zero(self):
        self.value = self.dim.zero()

    def add(self, other):
        new_value = ScalarValue(dim=self.dim)

        if isinstance(other, ScalarValue):
            new_value.set(self.value + other.value)
        elif isinstance(other, (int, float)):
            new_value.set(self.value + other)

        return new_value

    def sub(self, other):
        new_value = ScalarValue(dim=self.dim)

        if isinstance(other, ScalarValue):
            new_value.set(self.value - other.value)
        elif isinstance(other, (int, float)):
            new_value.set(self.value - other)

        return new_value

    def mul(self, other):
        new_value = ScalarValue(dim=self.dim)

        if isinstance(other, ScalarValue):
            new_value.set(self.value * other.value)
        elif isinstance(other, (int, float)):
            new_value.set(self.value * other)

        return new_value

    def imul(self, other):

        if isinstance(other, ScalarValue):
            self.set(self.value * other.value)
        elif isinstance(other, (int, float)):
            self.set(self.value * other)

        return self

    def iadd(self, other):
        if isinstance(other, ScalarValue):
            self.set(self.value + other.value)
        elif isinstance(other, (int, float)):
            self.set(self.value + other)
        return self

    def isub(self, other):
        if isinstance(other, ScalarValue):
            self.set(self.value - other.value)
        elif isinstance(other, (int, float)):
            self.set(self.value - other)
        return self

    # === BUILT-IN =====================================================================================================
    def __add__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.sub(other)

    def __isub__(self, other):
        return self.isub(other)

    def __iadd__(self, other):
        return self.iadd(other)

    def __mul__(self, other):
        return self.mul(other)

    def __imul__(self, other):
        return self.imul(other)

    def __rmul__(self, other):
        return self.mul(other)

    def __repr__(self):
        if self.value is not None:
            return f"[{self.dim.name}={self.value:.2}]"
        else:
            return f"[{self.dim.name}=None]"


# ======================================================================================================================
class VectorValue(StateValue):
    dim: VectorDimension
    value: np.ndarray

    def __init__(self, dim, value: (list, np.ndarray) = None):
        super().__init__()
        self.dim = dim
        self.value = self.dim.project(value=value)

    # ------------------------------------------------------------------------------------------------------------------
    def set(self, value, index: (int, str) = None):
        if index is None:
            if isinstance(value, (list, np.ndarray)):
                self.value = self.dim.project(value)
            elif isinstance(value, VectorValue):
                self.value = self.dim.project(value.value)
        elif isinstance(index, int):
            self.value[index] = self.dim.project(value, index)
        elif isinstance(index, str):
            dim_index = self.dim.dim_names.index(index)
            self.value[dim_index] = self.dim.project(value, dim_index)

    # ------------------------------------------------------------------------------------------------------------------
    def get(self, value, index: (int, str) = None):
        if index is None:
            return self.value
        elif isinstance(index, int):
            return self.value[index]
        elif isinstance(index, str):
            dim_index = self.dim.dim_names.index(index)
            return self.value[dim_index]

    # ------------------------------------------------------------------------------------------------------------------
    def add(self, other):
        new_value = VectorValue(dim=self.dim)
        # Case 1: Other value is also a vector in the same dimension
        if isinstance(other, VectorValue) and other.dim == self.dim:
            new_value.set(self.value + other.value)
            return new_value

        # Case 2: Other value is also a vector with the same number of dimensions:
        if isinstance(other, VectorValue) and other.dim.len == self.dim.len:
            new_value.set(self.value + other.value)
            return new_value

        # Case 3: other value is a list
        if isinstance(other, list) and len(other) == self.dim.len:
            new_value.set(self.value + np.asarray(other))
            return new_value

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            new_value.set(self.value + other)
            return new_value

        raise Exception()

    # ------------------------------------------------------------------------------------------------------------------
    def sub(self, other):
        new_value = VectorValue(dim=self.dim)
        # Case 1: Other value is also a vector in the same dimension
        if isinstance(other, VectorValue) and other.dim == self.dim:
            new_value.set(self.value - other.value)
            return new_value

        # Case 2: Other value is also a vector with the same number of dimensions:
        if isinstance(other, VectorValue) and other.dim.len == self.dim.len:
            new_value.set(self.value - other.value)
            return new_value

        # Case 3: other value is a list
        if isinstance(other, list) and len(other) == self.dim.len:
            new_value.set(self.value - np.asarray(other))
            return new_value

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            new_value.set(self.value - other)
            return new_value

        raise Exception()

    def mul(self, other):
        new_value = VectorValue(dim=self.dim)

        # Case 1: Other Value is a ScalarValue
        if isinstance(other, ScalarValue):
            new_value.set(self.value * other.value)
            return new_value

        # Case 2: Other is a scalar value
        if isinstance(other, (int, float)):
            new_value.set(self.value * other)
            return new_value

        # Case 3: Other is a matrix
        if isinstance(other, np.ndarray) and other.shape == (self.dim.len, self.dim.len):
            new_value.set(other @ self.value)
            return new_value

        raise Exception

    def matmul(self, other):
        new_value = VectorValue(dim=self.dim)
        if isinstance(other, np.ndarray) and other.shape == (self.dim.len, self.dim.len):
            new_value.set(other @ self.value)
            return new_value

        raise Exception

    def imul(self, other):
        # Case 1: Other Value is a ScalarValue
        if isinstance(other, ScalarValue):
            self.set(self.value * other.value)
            return self

        # Case 2: Other is a scalar value
        if isinstance(other, (int, float)):
            self.set(self.value * other)
            return self

        # Case 3: Other is a matrix
        if isinstance(other, np.ndarray) and other.shape == (self.dim.len, self.dim.len):
            self.set(other @ self.value)
            return self

        raise Exception

    def iadd(self, other):
        # Case 1: Other value is also a vector in the same dimension
        if isinstance(other, VectorValue) and other.dim == self.dim:
            self.set(self.value + other.value)
            return self

        # Case 2: Other value is also a vector with the same number of dimensions:
        if isinstance(other, VectorValue) and other.dim.len == self.dim.len:
            self.set(self.value + other.value)
            return self

        # Case 3: other value is a list
        if isinstance(other, list) and len(other) == self.dim.len:
            self.set(self.value + np.asarray(other))
            return self

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            self.set(self.value + other)
            return self

        raise Exception()

    def isub(self, other):
        # Case 1: Other value is also a vector in the same dimension
        if isinstance(other, VectorValue) and other.dim == self.dim:
            self.set(self.value - other.value)
            return self

        # Case 2: Other value is also a vector with the same number of dimensions:
        if isinstance(other, VectorValue) and other.dim.len == self.dim.len:
            self.set(self.value - other.value)
            return self

        # Case 3: other value is a list
        if isinstance(other, list) and len(other) == self.dim.len:
            self.set(self.value - np.asarray(other))
            return self

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            self.set(self.value - other)
            return self

        raise Exception()

    def zero(self):
        self.value = self.dim.zero()

    # === BUILT-IN =====================================================================================================
    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.set(value, key)
        elif isinstance(key, str):
            self.set(value, key)

    def __getitem__(self, key, value):
        if isinstance(key, int):
            return self.get(value, key)
        elif isinstance(key, str):
            return self.get(value, key)

    def __add__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.sub(other)

    def __iadd__(self, other):
        return self.iadd(other)

    def __isub__(self, other):
        return self.isub(other)

    def __mul__(self, other):
        return self.mul(other)

    def __imul__(self, other):
        return self.imul(other)

    def __rmul__(self, other):
        return self.mul(other)

    def __matmul__(self, other):
        return self.matmul(other)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if ufunc.__name__ == "matmul":
            return self.matmul(inputs[0])
        elif ufunc.__name__ == 'subtract':
            raise Exception("Not implemented yet!")
        elif ufunc.__name__ == 'multiply':
            return self.mul(inputs[0])
        elif ufunc.__name__ == 'add':
            raise Exception("Not implemented yet!")
        else:
            raise Exception("Not implemented yet!")

    def __repr__(self):
        out_str = '{:s}: ['.format(self.dim.name)
        for i, name in enumerate(self.dim.dim_names):
            out_str = out_str + "{:s} = {}, ".format(name, self.value[i])
        out_str = out_str[:-2] + ']'
        return out_str


# ======================================================================================================================
class MatrixValue(StateValue):
    dim: MatrixDimension
    value: np.ndarray

    def __init__(self, dim, value: (list, np.ndarray) = None):
        super().__init__()
        self.dim = dim
        self.value = self.dim.project(value)

    def set(self, value, index=None):
        if index is None:
            if isinstance(value, (list, np.ndarray)):
                self.value = self.dim.project(value)
            elif isinstance(value, MatrixValue):
                self.value = self.dim.project(value.value)
        elif isinstance(index, tuple):
            self.value[index] = value

    # ------------------------------------------------------------------------------------------------------------------
    def get(self, index=None):
        if index is None:
            return self.value
        elif isinstance(index, tuple):
            return self.value[index]

    # ------------------------------------------------------------------------------------------------------------------
    def add(self, other):
        new_value = MatrixValue(dim=self.dim)
        # Case 1: Other value is also a matrix in the same dimension
        if isinstance(other, MatrixValue) and other.dim == self.dim:
            new_value.set(self.value + other.value)
            return new_value

        # Case 2: Other value is also a matrix with the same number of dimensions:
        if isinstance(other, MatrixValue) and other.dim.shape == self.dim.shape:
            new_value.set(self.value + other.value)
            return new_value

        # Case 3: other value is a list
        if isinstance(other, list):
            new_value.set(self.value + np.asarray(other))
            return new_value

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            new_value.set(self.value + other)
            return new_value

        raise Exception()

    # ------------------------------------------------------------------------------------------------------------------
    def sub(self, other):
        new_value = MatrixValue(dim=self.dim)
        # Case 1: Other value is also a matrix in the same dimension
        if isinstance(other, MatrixValue) and other.dim == self.dim:
            new_value.set(self.value - other.value)
            return new_value

        # Case 2: Other value is also a matrix with the same number of dimensions:
        if isinstance(other, MatrixValue) and other.dim.shape == self.dim.shape:
            new_value.set(self.value - other.value)
            return new_value

        # Case 3: other value is a list
        if isinstance(other, list):
            new_value.set(self.value - np.asarray(other))
            return new_value

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            new_value.set(self.value - other)
            return new_value

        raise Exception()

    def iadd(self, other):

        # Case 1: Other value is also a matrix in the same dimension
        if isinstance(other, MatrixValue) and other.dim == self.dim:
            self.set(self.value + other.value)
            return self

        # Case 2: Other value is also a matrix with the same number of dimensions:
        if isinstance(other, MatrixValue) and other.dim.shape == self.dim.shape:
            self.set(self.value + other.value)
            return self

        # Case 3: other value is a list
        if isinstance(other, list):
            self.set(self.value + np.asarray(other))
            return self

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            self.set(self.value + other)
            return self

        raise Exception()

    # ------------------------------------------------------------------------------------------------------------------
    def isub(self, other):
        # Case 1: Other value is also a matrix in the same dimension
        if isinstance(other, MatrixValue) and other.dim == self.dim:
            self.set(self.value - other.value)
            return self

        # Case 2: Other value is also a matrix with the same number of dimensions:
        if isinstance(other, MatrixValue) and other.dim.shape == self.dim.shape:
            self.set(self.value - other.value)
            return self

        # Case 3: other value is a list
        if isinstance(other, list):
            self.set(self.value - np.asarray(other))
            return self

        # Case 4: Other value is a ndarray
        if isinstance(other, np.ndarray) and other.shape == self.value.shape:
            self.set(self.value - other)
            return self

        raise Exception()

    # ------------------------------------------------------------------------------------------------------------------
    def mul(self, other):
        new_value = MatrixValue(dim=self.dim)

        # Case 1: Other Value is a ScalarValue
        if isinstance(other, ScalarValue):
            new_value.set(self.value * other.value)
            return new_value

        # Case 2: Other is a scalar value
        if isinstance(other, (int, float)):
            new_value.set(self.value * other)
            return new_value

        # Case 3: Other is a MatrixValue
        if isinstance(other, MatrixValue):
            new_value.set(self.value @ other.value)
            return new_value

        # Case 4: Other is a np matrix
        if isinstance(other, np.ndarray) and len(other.shape) > 1:
            new_value.set(self.value @ other)
            return new_value

        # Case 5: Other is a VectorValue
        if isinstance(other, VectorValue):
            new_value = VectorValue(dim=other.dim)
            new_value.set(self.value @ other.value)
            return new_value

        # Case 6: Other is a np array
        if isinstance(other, np.ndarray) and len(other.shape) == 1:
            return self.value @ other

        raise Exception

    def rmul(self, other):
        new_value = MatrixValue(dim=self.dim)

        # Case 1: Other Value is a ScalarValue
        if isinstance(other, ScalarValue):
            new_value.set(self.value * other.value)
            return new_value

        # Case 2: Other is a scalar value
        if isinstance(other, (int, float)):
            new_value.set(self.value * other)
            return new_value

        # Case 3: Other is a MatrixValue
        if isinstance(other, MatrixValue):
            new_value.set(other.value @ self.value)
            return new_value

        # Case 4: Other is a np matrix
        if isinstance(other, np.ndarray):
            new_value.set(other @ self.value)
            return new_value

        raise Exception

    def matmul(self, other):
        new_value = MatrixValue(dim=self.dim)
        if isinstance(other, np.ndarray):
            new_value.set(self.value @ other)
            return new_value
        if isinstance(other, MatrixValue):
            new_value.set(self.value @ other.value)
            return new_value
        raise Exception

    def rmatmul(self, other):
        new_value = MatrixValue(dim=self.dim)
        if isinstance(other, np.ndarray):
            new_value.set(other @ self.value)
            return new_value
        if isinstance(other, MatrixValue):
            new_value.set(other.value @ self.value)
            return new_value
        raise Exception

    def imul(self, other):
        # Case 1: Other Value is a ScalarValue
        if isinstance(other, ScalarValue):
            self.set(self.value * other.value)
            return self

        # Case 2: Other is a scalar value
        if isinstance(other, (int, float)):
            self.set(self.value * other)
            return self

        # Case 3: Other is a MatrixValue
        if isinstance(other, MatrixValue):
            self.set(self.value @ other.value)
            return self

        # Case 4: Other is a np matrix
        if isinstance(other, np.ndarray):
            self.set(self.value @ other)
            return self

        raise Exception

    # === BUILT-IN =====================================================================================================
    def __setitem__(self, key, value):
        self.set(value, key)

    #
    def __getitem__(self, key):
        return self.get(key)

    def __add__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.sub(other)

    def __iadd__(self, other):
        return self.iadd(other)

    def __isub__(self, other):
        return self.isub(other)

    def __mul__(self, other):
        return self.mul(other)

    def __imul__(self, other):
        return self.imul(other)

    def __rmul__(self, other):
        return self.rmul(other)

    def __matmul__(self, other):
        return self.matmul(other)

    def __rmatmul__(self, other):
        return self.rmatmul(other)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if ufunc.__name__ == "matmul":
            return self.matmul(inputs[0])
        elif ufunc.__name__ == 'subtract':
            raise Exception("Not implemented yet!")
        elif ufunc.__name__ == 'multiply':
            return self.mul(inputs[0])
        elif ufunc.__name__ == 'add':
            raise Exception("Not implemented yet!")
        else:
            raise Exception("Not implemented yet!")

    #
    def __repr__(self):
        out_str = '{:s}: '.format(self.dim.name) + str(self.value.tolist().__repr__())
        return out_str


# ======================================================================================================================

class Space:
    dimensions: list[Dimension]
    mappings: list
    name: str

    def __init__(self, dimensions: (int, list)):
        if isinstance(dimensions, int):
            self.dimensions = []
            for i in range(0, dimensions):
                self.dimensions.append(Dimension(name='dim_' + str(i)))

        elif isinstance(dimensions, list):
            self.dimensions = []

            for dimension in dimensions:
                if isinstance(dimension, str):
                    self.dimensions.append(Dimension(name=dimension))
                elif isinstance(dimension, Dimension):
                    self.dimensions.append(dimension)

        self.mappings = []

    # == METHODS =======================================================================================================
    def zero(self):
        out = State(space=self)
        for dim in self.dimensions:
            value = dim.zero()
            out[dim.name] = value
        return out

    def none(self):
        out = State(space=self)
        for dim in self.dimensions:
            out[dim.name] = None
        return out

    # ------------------------------------------------------------------------------------------------------------------
    def map(self, state):

        if state is None:
            return None

        # Condition 1: State is from this space
        if isinstance(state, State) and state.space == self:
            new_state = State(space=self)
            new_state.set(state.value)
            return new_state

        # Condition 2: State is a 'State' from another space, but there exists a mapping
        if isinstance(state, State) and state.space.has_mapping(self):
            mapping = next((mapping for mapping in self.mappings if state.space in mapping), None)
            if mapping is not None:
                return mapping.map(state)

        # Condition 3: State is a list of the correct length
        if isinstance(state, list) and len(state) == self.dof:
            new_state = State(space=self)
            for i, dim in enumerate(self.dimensions):
                new_state.set(state[i], i)
            return new_state

        # Condition 4: State is a ndarray of the correct length
        if isinstance(state, np.ndarray) and state.shape == (self.dof,):
            new_state = State(space=self)
            for i, dim in enumerate(self.dimensions):
                new_state[i] = dim.project(state[i])
            return new_state

        # Condition 5: State is a numeric value and the space is only 1D:
        if isinstance(state, (int, float)) and self.dof == 1:
            new_state = State(space=self)
            new_state[0] = self.dimensions[0].project(state)
            return new_state

        raise Exception()

    # ------------------------------------------------------------------------------------------------------------------
    def add_mapping(self, mapping):
        assert (isinstance(mapping, Mapping) or (
                isinstance(mapping, list) and all([isinstance(elem, Mapping) for elem in mapping])))

        if mapping not in self.mappings:
            self.mappings.append(mapping)

    # ------------------------------------------------------------------------------------------------------------------
    def has_mapping(self, space):
        if space == self:
            return True
        elif any([elem for elem in self.mappings if space in elem]):
            return True
        elif self.dof == space.dof and all(
                [self.dimensions[i].name == space.width[i].name for i in range(0, self.dof)]):
            return True
        return False

    # ------------------------------------------------------------------------------------------------------------------
    def hasDimension(self, dimension: str):
        if dimension in self.dim_names:
            return True
        else:
            return False

    # == PROPERTIES ====================================================================================================
    @property
    def dof(self):
        return len(self.dimensions)

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def dim_names(self):
        out = []
        for dim in self.dimensions:
            out.append(dim.name)
        return out

    # ------------------------------------------------------------------------------------------------------------------
    def add(self, state1, state2):
        state_out = self.none()
        state1_map = self.map(state1)
        state2_map = self.map(state2)

        for i, dim in enumerate(self.dimensions):
            state_out[i] = state1_map[i] + state2_map[i]

        return state_out

    def iadd(self, state1, state2):
        state2_map = self.map(state2)
        for i, dim in enumerate(self.dimensions):
            state1[i] = state1[i] + state2_map[i]
        return state1

    def sub(self, state1, state2):
        state_out = self.none()
        state1_map = self.map(state1)
        state2_map = self.map(state2)

        for i, dim in enumerate(self.dimensions):
            state_out[i] = state1_map[i] - state2_map[i]

        return state_out

    def isub(self, state1, state2):
        state2_map = self.map(state2)
        for i, dim in enumerate(self.dimensions):
            state1[i] = state1[i] - state2_map[i]
        return state1

    # def scalar_mult(self, state, scalar):
    #     state_out = self.none()
    #     for i, dim in enumerate(self.dimensions):
    #         state_out[i] = dim.scalar_mult(state[i], scalar)
    #     return state_out
    #
    # def scalar_imul(self, state, scalar):
    #     for i, dim in enumerate(self.dimensions):
    #         state[i] = dim.scalar_mult(state[i], scalar)
    #     return state

    def concat(self, state1, state2):
        print("CONCAT")

    # == BUILT INS =====================================================================================================
    def __repr__(self):
        return f"{self.dimensions}"

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.dimensions[item]
        if isinstance(item, str):
            return next((dim for dim in self.dimensions if dim.name == item), None)


# ======================================================================================================================
class State:
    space: Space
    value: list[StateValue]

    def __init__(self, space, value=None):

        self.space = space
        self.value = []

        for dim in self.space.dimensions:
            if isinstance(dim, MatrixDimension):
                self.value.append(MatrixValue(dim=dim))
            elif isinstance(dim, VectorDimension):
                self.value.append(VectorValue(dim=dim))
            elif isinstance(dim, Dimension):
                self.value.append(ScalarValue(dim=dim))

        if value is not None:
            self.set(value)

    # == PROPERTIES ====================================================================================================
    # @property
    # def T(self):
    #     if all([dim.datatype == float for dim in self.space.dimensions]):
    #         return np.transpose(self.value)
    #     else:
    #         return None

    # @property
    # def _names(self):
    #     return [dimension.name for dimension in self.space.dimensions]

    # == METHODS =======================================================================================================
    def set(self, value, index=None):
        if index is None:
            assert (len(value) == len(self.space.dimensions))
            for i, elem in enumerate(value):
                self.value[i].set(elem)
        elif isinstance(index, int):
            self.value[index].set(value)
        elif isinstance(index, str):
            dim_index = self.space.dim_names.index(index)
            self.value[dim_index].set(value)

    # ------------------------------------------------------------------------------------------------------------------
    def get(self, index):
        if isinstance(index, int):
            return self.value[index]
        elif isinstance(index, str):
            dim_index = self.space.dim_names.index(index)
            return self.value[dim_index]

    # ------------------------------------------------------------------------------------------------------------------

    # def empty(self):
    #     self.value = []
    #     for i, dim in enumerate(self.space.dimensions):
    #         self.value.append(dim.none())
    #
    # # == PRIVATE METHODS =============================================================================================
    # def _index(self, key):
    #     idx = next((idx for idx, element in enumerate(self.space.dimensions) if element.name == key), None)
    #     if idx is None:
    #         raise Exception("Index not found")
    #     return idx

    # == BUILT-INS =====================================================================================================
    def __setitem__(self, key, value):
        assert (isinstance(key, (int, str)))
        self.set(value, key)

    # ------------------------------------------------------------------------------------------------------------------
    def __getitem__(self, item):
        assert (isinstance(item, (int, str, slice)))
        return self.get(item)

    # ------------------------------------------------------------------------------------------------------------------
    def __add__(self, other):
        return self.space.add(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __iadd__(self, other):
        return self.space.iadd(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __radd__(self, other):
        return self.space.add(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __sub__(self, other):
        return self.space.sub(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __rsub__(self, other):
        return self.space.sub(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __isub__(self, other):
        return self.space.isub(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    # def __mul__(self, other):
    #     if isinstance(other, (int, float)):
    #         return self.space.scalar_mult(self, other)
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def __imul__(self, other):
    #     if isinstance(other, (int, float)):
    #         return self.space.scalar_imul(self, other)
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def __rmul__(self, other):
    #     if isinstance(other, (int, float)):
    #         return self.space.scalar_mult(self, other)
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def __matmul__(self, other):
    #     pass
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def __rmatmul__(self, other):
    #     assert self.space.cartesian
    #     assert (isinstance(other, np.ndarray))
    #     assert (other.shape[1] == len(self.space.dimensions))
    #
    #     if other.shape[0] == other.shape[1]:  # quadratic matrix. Retains original state structure
    #         self_copy = cp.copy(self)
    #         self_copy.value = np.asarray(other @ self.value)
    #         return self_copy
    #     else:
    #         self_copy = cp.copy(self)
    #         self_copy.value = np.asarray(other @ self.value)
    #         return self_copy

    def __rshift__(self, other):
        return self.space.concat(self, other)

    # ------------------------------------------------------------------------------------------------------------------
    def __iter__(self):
        for i in self.value:
            yield i
        return

    # ------------------------------------------------------------------------------------------------------------------
    def __len__(self):
        return len(self.value)

    # ------------------------------------------------------------------------------------------------------------------
    # def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
    #     if ufunc.__name__ == "matmul":
    #         return self.__rmatmul__(inputs[0])
    #     elif ufunc.__name__ == 'subtract':
    #         return self.__rsub__(inputs[0])
    #     elif ufunc.__name__ == 'multiply':
    #         return self.__mul__(inputs[0])
    #     elif ufunc.__name__ == 'add':
    #         return self.__radd__(inputs[0])
    #     else:
    #         raise Exception("Not implemented yet!")

    # ------------------------------------------------------------------------------------------------------------------
    def __copy__(self):
        return self.__deepcopy__(self)

    # ------------------------------------------------------------------------------------------------------------------
    def __deepcopy__(self, memodict=None):
        if memodict is None:
            memodict = {}
        copy = type(self)(value=cp.copy(self.value), space=self.space)
        return copy
        # memo[id(self)] = copy
        # copy.space = self.space

    # ------------------------------------------------------------------------------------------------------------------
    def __repr__(self):
        out_str = '['
        for i, dim in enumerate(self.space.dimensions):
            out_str = out_str + "{}, ".format(self.value[i])
        out_str = out_str[:-2] + ']'
        return out_str


# ======================================================================================================================
class Mapping:
    space_from: Space
    space_to: Space

    def __init__(self, space_from: Space, space_to: Space, mapping, inverse=None):
        self.space_from = space_from
        self.space_to = space_to
        self.mapping = mapping
        self.inverse = inverse

        self.space_from.add_mapping(self)
        self.space_to.add_mapping(self)

    # == METHODS =======================================================================================================
    def map(self, state):
        assert (isinstance(state, State) and (state.space == self.space_from or state.space == self.space_to))
        if state.space == self.space_from:
            return State(space=self.space_to, value=self.mapping(state))
        elif state.space == self.space_to:
            return State(space=self.space_from, value=self.inverse(state))

    # == PRIVATE METHODS ===============================================================================================
    def __contains__(self, item):
        if isinstance(item, Space):
            if item == self.space_from or item == self.space_to:
                return True
        elif isinstance(item, State):
            if item.space == self.space_from or item.space == self.space_to:
                return True
        return False


# ======================================================================================================================
# Special Spaces and Dimensions


# class OrientationMatrix2D(Dimension):
#     def __init__(self, name):
#         super().__init__(name, dimension=(2, 2), datatype=np.ndarray, dimension_type='matrix')
#
#     def concat(self, value1, value2):
#         result = value1 @ value2
#         return result
#
#     def zero(self):
#         return np.eye(2)


class OrientationMatrix3D(MatrixValue):
    ...


class OrientationMatrix3D_Dimension(MatrixDimension):

    def __init__(self, name='ori'):
        super().__init__(name, shape=(3, 3))

    # def concat(self, value1, value2):
    #     result = value1 @ value2
    #     return result

    def zero(self):
        return np.eye(3)

    def getHeading(self, value: MatrixValue):
        return orientation_utils.psiFromRotMat(value.value)


class PositionVector3D_Dimension(VectorDimension):
    def __init__(self, name='pos', limits: list = None, wrapping: bool = False):
        super().__init__(name=name, shape=(3,), names=['x', 'y', 'z'], limits=limits, wrapping=wrapping,
                         discretization=None)


class PositionVector2D_Dimension(VectorDimension):
    def __init__(self, name='pos', limits: list = None, wrapping: bool = False):
        super().__init__(name=name, shape=(2,), names=['x', 'y'], limits=limits, wrapping=wrapping,
                         discretization=None)


class PositionVector3D(VectorValue):
    def __init__(self, dim=None):
        if dim is None:
            dim = PositionVector3D_Dimension()
        super().__init__(dim=dim)


class PositionVector2D(VectorValue):
    def __init__(self, dim=None):
        if dim is None:
            dim = PositionVector2D_Dimension()
        super().__init__(dim=dim)


class Space3D(Space):
    def __init__(self):
        super().__init__(dimensions=[PositionVector3D_Dimension(name='pos'), OrientationMatrix3D_Dimension()])

    def add(self, state1, state2):
        print("NOT DEFINED")
