"""!

@brief Neural Network: Self-Organized Feature Map
@details Based on article description:
         - T.Kohonen. The Self-Organizing Map. 1990.
         - T.Kohonen, E.Oja, O.Simula, A.Visa, J.Kangas. Engineering Applications of the Self-Organizing Map. 1996.

@authors Andrei Novikov (pyclustering@yandex.ru)
@date 2014-2015
@copyright GNU Public License

@cond GNU_PUBLIC_LICENSE
    PyClustering is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    PyClustering is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
@endcond

"""


import math;
import random;

import matplotlib.pyplot as plt;

import pyclustering.core.som_wrapper as wrapper;

from pyclustering.utils import euclidean_distance_sqrt;

from enum import IntEnum;


class type_conn(IntEnum):
    """!
    @brief Enumeration of connection types for SOM.
    
    @see som
    
    """
    
    ## Grid type of connections when each oscillator has connections with left, upper, right, lower neighbors.
    grid_four = 0;
    
    ## Grid type of connections when each oscillator has connections with left, upper-left, upper, upper-right, right, right-lower, lower, lower-left neighbors.
    grid_eight = 1;
    
    ## Grid type of connections when each oscillator has connections with left, upper-left, upper-right, right, right-lower, lower-left neighbors.
    honeycomb = 2;
    
    ## Grid type of connections when existance of each connection is defined by the SOM rule on each step of simulation.
    func_neighbor = 3;
    
    
class type_init(IntEnum):
    """!
    @brief Enumeration of initialization types for SOM
    
    @see som
    
    """
    
    ## Weights are randomly distributed using Gaussian distribution (0, 1).
    random = 0;
    
    ## Weights are randomly distributed using Gaussian distribution (input data centroid, 1).
    random_centroid = 1;
    
    ## Weights are randomly distrbiuted using Gaussian distribution (input data centroid, surface of input data).
    random_surface = 2;
    
    ## Weights are distributed as a uniform grid that covers whole surface of the input data.
    uniform_grid = 3;


class som_parameters:
    """!
    @brief Represents SOM parameters.
    
    """
    
    ## Type of initialization of initial neuron weights (random, random in center of the input data, random distributed in data, ditributed in line with uniform grid).
    init_type = type_init.uniform_grid; 
    
    ## Initial radius (if not specified then will be calculated by SOM). 
    init_radius = None;
    
    ## Rate of learning.   
    init_learn_rate = 0.1;
    
    ## Condition when learining process should be stoped. It's used when autostop mode is used. 
    adaptation_threshold = 0.001; 


class som:
    """!
    @brief Represents self-organized feature map (SOM).
    
    Example:
    @code
        # sample for training
        sample_train = read_sample(file_train_sample);
        
        # create self-organized feature map with size 5x5
        network = som(5, 5, sample_train, 100);
        
        # train network
        network.train();
        
        # simulate using another sample
        sample = read_sample(file_sample);
        index_winner = network.simulate(sample);
        
        # check what it is (what it looks like?)
        index_similar_objects = network.capture_objects[index_winner];
        
    @endcode
        
    """
    
    # describe network
    _rows = 0;
    _cols = 0;
    _size = 0;
    _weights = None;        # Weights of each neuron (coordinates in data dimension in other words).
    _award = None;          # Lists of indexes of won points for each neuron.
    _data = None;           # Analyzed data.
    _conn_type = None;      # Type of connections between neuron.
    
    # just for convenience (avoid excess calculation during learning)
    _location = None;           # Location in grid.
    _sqrt_distances = None;
    _capture_objects = None;    # Store indexes of input points that were captured by each neurons individually at the end.
    _neighbors = None;          # Indexes of neighbours for each neuron.
    
    # describe learning process and internal state
    _epochs = 0;                    # Iteration for learning.
    _params = None;
    
    # dynamic changes learning parameters
    _local_radius = 0.0;
    _learn_rate = 0.0;
    
    __ccore_som_pointer = None;
    
    
    @property
    def size(self):
        """!
        @return (uint) Size of self-organized map (number of neurons).
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._size = wrapper.som_get_size(self.__ccore_som_pointer);
            
        return self._size;
    
    @property
    def weights(self):
        """!
        @return (list) Weights of each neuron.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._weights = wrapper.som_get_weights(self.__ccore_som_pointer);
        
        return self._weights;
    
    @property
    def awards(self):
        """!
        @return (list) Numbers of captured objects by each neuron.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._award = wrapper.som_get_awards(self.__ccore_som_pointer);
        
        return self._award;
    
    @property
    def capture_objects(self):
        """!
        @return (list) Indexes of captured objects by each neuron.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._capture_objects = wrapper.som_get_capture_objects(self.__ccore_som_pointer);
        
        return self._capture_objects;
    
    
    def __init__(self, rows, cols, conn_type = type_conn.grid_eight, parameters = None, ccore = False):
        """!
        @brief Constructor of self-organized map.
        
        @param[in] rows (uint): Number of neurons in the column (number of rows).
        @param[in] cols (uint): Number of neurons in the row (number of columns).
        @param[in] conn_type (type_conn): Type of connection between oscillators in the network (grid four, grid eight, honeycomb, function neighbour).
        @param[in] parameters (som_parameters): Other specific parameters.
        @param[in] ccore (bool): If True simulation is performed by CCORE library (C++ implementation of pyclustering).
        
        """
        
        # some of these parameters are required despite core implementation, for example, for network demonstration.
        self._cols = cols;
        self._rows = rows;        
        self._size = cols * rows;
        self._conn_type = conn_type;
        
        if (parameters is not None):
            self._params = parameters;
        else:
            self._params = som_parameters();
            
        if (self._params.init_radius is None):
            if ((cols + rows) / 4.0 > 1.0): 
                self._params.init_radius = 2.0;
            elif ( (cols > 1) and (rows > 1) ): 
                self._params.init_radius = 1.5;
            else: 
                self._params.init_radius = 1.0;
        
        if (ccore is True):
            self.__ccore_som_pointer = wrapper.som_create(rows, cols, conn_type, self._params);
            
        else:
            # location
            self._location = list();
            for i in range(self._rows):
                for j in range(self._cols):
                    self._location.append([float(i), float(j)]);
            
            # awards
            self._award = [0] * self._size;
            self._capture_objects = [ [] for i in range(self._size) ];
            
            # distances
            self._sqrt_distances = [ [ [] for i in range(self._size) ] for j in range(self._size) ];
            for i in range(self._size):
                for j in range(i, self._size, 1):
                    dist = euclidean_distance_sqrt(self._location[i], self._location[j]);
                    self._sqrt_distances[i][j] = dist;
                    self._sqrt_distances[j][i] = dist;
        
            # connections
            if (conn_type != type_conn.func_neighbor):
                self._create_connections(conn_type);
        

    def __del__(self):
        """!
        @brief Destructor of the self-organized feature map.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            wrapper.som_destroy(self.__ccore_som_pointer);
            
    
    def __len__(self):
        """!
        @return (uint) Size of self-organized map (number of neurons).
        
        """
        
        return self.size;
    
    
    def _create_initial_weights(self, init_type):
        """!
        @brief Creates initial weights for neurons in line with the specified initialization.
        
        @param[in] init_type (type_init): Type of initialization of initial neuron weights (random, random in center of the input data, random distributed in data, ditributed in line with uniform grid).
        
        """
        
        dimension = len(self._data[0]);
        
        maximum_dimension = [self._data[0][i] for i in range(dimension)];
        minimum_dimension = [self._data[0][i] for i in range(dimension)];
        for i in range(len(self._data)):
            for dim in range(dimension):
                if (maximum_dimension[dim] < self._data[i][dim]):
                    maximum_dimension[dim] = self._data[i][dim];
                elif (minimum_dimension[dim] > self._data[i][dim]):
                    minimum_dimension[dim] = self._data[i][dim];
                     
        # Increase border
        width_dimension = [0] * dimension;
        center_dimension = [0] * dimension;
        for dim in range(dimension):            
            width_dimension[dim] = maximum_dimension[dim] - minimum_dimension[dim];
            center_dimension[dim] = (maximum_dimension[dim] + minimum_dimension[dim]) / 2;
        
        step_x = center_dimension[0];
        if (self._rows > 1): step_x = width_dimension[0] / (self._rows - 1);
        
        step_y = 0.0;
        if (dimension > 1):
            step_y = center_dimension[1];
            if (self._cols > 1): step_y = width_dimension[1] / (self._cols - 1); 
                      
        # generate weights (topological coordinates)
        random.seed();
        
        # Feature SOM 0002: Uniform grid.
        if (init_type == type_init.uniform_grid):
            # Predefined weights in line with input data.
            self._weights = [ [ [] for i in range(dimension) ] for j in range(self._size)];
            for i in range(self._size):
                location = self._location[i];
                for dim in range(dimension):
                    if (dim == 0):
                        if (self._rows > 1):
                            self._weights[i][dim] = minimum_dimension[dim] + step_x * location[dim];
                        else:
                            self._weights[i][dim] = center_dimension[dim];
                            
                    elif (dim == 1):
                        if (self._cols > 1):
                            self._weights[i][dim] = minimum_dimension[dim] + step_y * location[dim];
                        else:
                            self._weights[i][dim] = center_dimension[dim];
                    else:
                        self._weights[i][dim] = center_dimension[dim];
        
        elif (init_type == type_init.random_surface):    
            # Random weights at the full surface.
            self._weights = [ [random.uniform(minimum_dimension[i], maximum_dimension[i]) for i in range(dimension)] for j in range(self._size) ];
            
        elif (init_type == type_init.random_centroid):
            # Random weights at the center of input data.
            self._weights = [ [(random.random() + center_dimension[i])  for i in range(dimension)] for j in range(self._size) ];        
        
        else:
            # Random weights of input data.
            self._weights = [ [random.random()  for i in range(dimension)] for j in range(self._size) ]; 
    
    def _create_connections(self, conn_type):
        """!
        @brief Create connections in line with input rule (grid four, grid eight, honeycomb, function neighbour).
        
        @param[in] conn_type (type_conn): Type of connection between oscillators in the network.
        
        """
        
        self._neighbors = [[] for index in range(self._size)];    
            
        for index in range(0, self._size, 1):
            upper_index = index - self._cols;
            upper_left_index = index - self._cols - 1;
            upper_right_index = index - self._cols + 1;
            
            lower_index = index + self._cols;
            lower_left_index = index + self._cols - 1;
            lower_right_index = index + self._cols + 1;
            
            left_index = index - 1;
            right_index = index + 1;
            
            node_row_index = math.floor(index / self._cols);
            upper_row_index = node_row_index - 1;
            lower_row_index = node_row_index + 1;
            
            if ( (conn_type == type_conn.grid_eight) or (conn_type == type_conn.grid_four) ):
                if (upper_index >= 0):
                    self._neighbors[index].append(upper_index);
                    
                if (lower_index < self._size):
                    self._neighbors[index].append(lower_index);
            
            if ( (conn_type == type_conn.grid_eight) or (conn_type == type_conn.grid_four) or (conn_type == type_conn.honeycomb) ):
                if ( (left_index >= 0) and (math.floor(left_index / self._cols) == node_row_index) ):
                    self._neighbors[index].append(left_index);
                
                if ( (right_index < self._size) and (math.floor(right_index / self._cols) == node_row_index) ):
                    self._neighbors[index].append(right_index);  
                
                
            if (conn_type == type_conn.grid_eight):
                if ( (upper_left_index >= 0) and (math.floor(upper_left_index / self._cols) == upper_row_index) ):
                    self._neighbors[index].append(upper_left_index);
                
                if ( (upper_right_index >= 0) and (math.floor(upper_right_index / self._cols) == upper_row_index) ):
                    self._neighbors[index].append(upper_right_index);
                    
                if ( (lower_left_index < self._size) and (math.floor(lower_left_index / self._cols) == lower_row_index) ):
                    self._neighbors[index].append(lower_left_index);
                    
                if ( (lower_right_index < self._size) and (math.floor(lower_right_index / self._cols) == lower_row_index) ):
                    self._neighbors[index].append(lower_right_index);          
                
            
            if (conn_type == type_conn.honeycomb):
                if ( (node_row_index % 2) == 0):
                    upper_left_index = index - self._cols;
                    upper_right_index = index - self._cols + 1;
                
                    lower_left_index = index + self._cols;
                    lower_right_index = index + self._cols + 1;
                else:
                    upper_left_index = index - self._cols - 1;
                    upper_right_index = index - self._cols;
                
                    lower_left_index = index + self._cols - 1;
                    lower_right_index = index + self._cols;
                
                if ( (upper_left_index >= 0) and (math.floor(upper_left_index / self._cols) == upper_row_index) ):
                    self._neighbors[index].append(upper_left_index);
                
                if ( (upper_right_index >= 0) and (math.floor(upper_right_index / self._cols) == upper_row_index) ):
                    self._neighbors[index].append(upper_right_index);
                    
                if ( (lower_left_index < self._size) and (math.floor(lower_left_index / self._cols) == lower_row_index) ):
                    self._neighbors[index].append(lower_left_index);
                    
                if ( (lower_right_index < self._size) and (math.floor(lower_right_index / self._cols) == lower_row_index) ):
                    self._neighbors[index].append(lower_right_index);                        
    
    
    def _competition(self, x):
        """!
        @brief Calculates neuron winner (distance, neuron index).
        
        @param[in] x (list): Input pattern from the input data set, for example it can be coordinates of point.
        
        @return (uint) Returns index of neuron that is winner.
        
        """
        
        index = 0;
        minimum = euclidean_distance_sqrt(self._weights[0], x);
        
        for i in range(1, self._size, 1):
            candidate = euclidean_distance_sqrt(self._weights[i], x);
            if (candidate < minimum):
                index = i;
                minimum = candidate;
        
        return index;
    
    
    def _adaptation(self, index, x):
        """!
        @brief Change weight of neurons in line with won neuron.
        
        @param[in] index (uint): Index of neuron-winner.
        @param[in] x (list): Input pattern from the input data set.
        
        """
        
        dimension = len(self._weights[0]);
        
        if (self._conn_type == type_conn.func_neighbor):
            for neuron_index in range(self._size):
                distance = self._sqrt_distances[index][neuron_index];
                
                if (distance < self._local_radius):
                    influence = math.exp( -( distance / (2.0 * self._local_radius) ) );
                    
                    for i in range(dimension):
                        self._weights[neuron_index][i] = self._weights[neuron_index][i] + self._learn_rate * influence * (x[i] - self._weights[neuron_index][i]); 
                    
        else:
            for i in range(dimension):
                self._weights[index][i] = self._weights[index][i] + self._learn_rate * (x[i] - self._weights[index][i]); 
                
            for neighbor_index in self._neighbors[index]: 
                distance = self._sqrt_distances[index][neighbor_index]
                if (distance < self._local_radius):
                    influence = math.exp( -( distance / (2.0 * self._local_radius) ) );
                    
                    for i in range(dimension):       
                        self._weights[neighbor_index][i] = self._weights[neighbor_index][i] + self._learn_rate * influence * (x[i] - self._weights[neighbor_index][i]);  
    
                            
    def train(self, data, epochs, autostop = False):
        """!
        @brief Trains self-organized feature map (SOM).

        @param[in] data (list): Input data - list of points where each point is represented by list of features, for example coordinates.
        @param[in] epochs (uint): Number of epochs for training.        
        @param[in] autostop (bool): Automatic termination of learining process when adaptation is not occurred.
        
        @return (uint) Number of learining iterations.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            return wrapper.som_train(self.__ccore_som_pointer, data, epochs, autostop);
        
        for i in range(self._size):
            self._award[i] = 0;
            self._capture_objects[i].clear();
            
        self._epochs = epochs;
        self._data = data;
        
        # weights
        self._create_initial_weights(self._params.init_type);
        
        previous_weights = None;
        
        for epoch in range(1, self._epochs + 1):
            # Depression term of coupling
            self._local_radius = ( self._params.init_radius * math.exp(-(epoch / self._epochs)) ) ** 2;
            self._learn_rate = self._params.init_learn_rate * math.exp(-(epoch / self._epochs));

            #random.shuffle(self._data);    # Random order
            
            # Feature SOM 0003: Clear statistics
            if (autostop == True):
                for i in range(self._size):
                    self._award[i] = 0;
                    self._capture_objects[i].clear();
            
            for i in range(len(self._data)):
                # Step 1: Competition:
                index = self._competition(self._data[i]);
                    
                # Step 2: Adaptation:   
                self._adaptation(index, self._data[i]);
                
                # Update statistics
                if ( (autostop == True) or (epoch == self._epochs) ):
                    self._award[index] += 1;
                    self._capture_objects[index].append(i);
            
            # Feature SOM 0003: Check requirement of stopping
            if (autostop == True):
                if (previous_weights is not None):
                    maximal_adaptation = self._get_maximal_adaptation(previous_weights);
                    if (maximal_adaptation < self._params.adaptation_threshold):
                        return epoch;
            
                previous_weights = [item[:] for item in self._weights];
        
        return self._epochs;
    
    def simulate(self, input_pattern):
        """!
        @brief Processes input pattern (no learining) and returns index of neuron-winner.
               Using index of neuron winner catched object can be obtained using property capture_objects.
               
        @param[in] input_pattern (list): Input pattern.
        
        @return (uint) Returns index of neuron-winner.
               
        @see capture_objects
        
        """
                
        if (self.__ccore_som_pointer is not None):
            return wrapper.som_simulate(self.__ccore_som_pointer, [ input_pattern ]);
            
        return self._competition(input_pattern);
    
    
    def _get_maximal_adaptation(self, previous_weights):
        """!
        @brief Calculates maximum changes of weight in line with comparison between previous weights and current weights.
        
        @param[in] previous_weights (list): Weights from the previous step of learning process.
        
        @return (double) Value that represents maximum changes of weight after adaptation process.
        
        """
        
        dimension = len(self._data[0]);
        maximal_adaptation = 0.0;
        
        for neuron_index in range(self._size):
            for dim in range(dimension):
                current_adaptation = previous_weights[neuron_index][dim] - self._weights[neuron_index][dim];
                        
                if (current_adaptation < 0): current_adaptation = -current_adaptation;
                        
                if (maximal_adaptation < current_adaptation):
                    maximal_adaptation = current_adaptation;
                    
        return maximal_adaptation;
    
    
    def get_winner_number(self):
        """!
        @brief Calculates number of winner at the last step of learning process.
        
        @return (uint) Number of winner.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._award = wrapper.som_get_awards(self.__ccore_som_pointer);
        
        winner_number = 0;
        for i in range(self._size):
            if (self._award[i] > 0):
                winner_number += 1;
                
        return winner_number;
    
    
    def show_distance_matrix(self):
        """!
        @brief Shows gray visualization of U-matrix (distance matrix).
        
        @see get_distance_matrix()
        
        """
        distance_matrix = self.get_distance_matrix();
        
        plt.imshow(distance_matrix, cmap = plt.get_cmap('hot'), interpolation='kaiser');
        plt.title("U-Matrix");
        plt.colorbar();
        plt.show();

    
    def get_distance_matrix(self):
        """!
        @brief Calculates distance matrix (U-matrix).
        @details The U-Matrix visualizes based on the distance in input space between a weight vector and its neighbors on map.
        
        @return (list) Distance matrix (U-matrix).
        
        @see show_distance_matrix()
        @see get_density_matrix()
        
        """
        if (self.__ccore_som_pointer is not None):
            self._weights = wrapper.som_get_weights(self.__ccore_som_pointer);
            
            if (self._conn_type != type_conn.func_neighbor):
                self._neighbors = wrapper.som_get_neighbors(self.__ccore_som_pointer);
            
        distance_matrix = [ [0.0] * self._cols for i in range(self._rows) ];
        
        for i in range(self._rows):
            for j in range(self._cols):
                neuron_index = i * self._cols + j;
                
                if (self._conn_type == type_conn.func_neighbor):
                    self._create_connections(type_conn.grid_eight);
                
                for neighbor_index in self._neighbors[neuron_index]:
                    distance_matrix[i][j] += euclidean_distance_sqrt(self._weights[neuron_index], self._weights[neighbor_index]);
                    
                distance_matrix[i][j] /= len(self._neighbors[neuron_index]);
    
        return distance_matrix;
    
    
    def show_density_matrix(self, surface_divider = 20.0):
        """!
        @brief Show density matrix (P-matrix) using kernel density estimation.
        
        @param[in] surface_divider (double): Divider in each dimension that affect radius for density measurement.
        
        @see show_distance_matrix()
        
        """        
        density_matrix = self.get_density_matrix();
        
        plt.imshow(density_matrix, cmap = plt.get_cmap('hot'), interpolation='kaiser');
        plt.title("P-Matrix");
        plt.colorbar();
        plt.show();
    
    
    def get_density_matrix(self, surface_divider = 20.0):
        """!
        @brief Calculates density matrix (P-Matrix).
        
        @param[in] surface_divider (double): Divider in each dimension that affect radius for density measurement.
        
        @return (list) Density matrix (P-Matrix).
        
        @see get_distance_matrix()
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._weights = wrapper.som_get_weights(self.__ccore_som_pointer);
        
        density_matrix = [ [0] * self._cols for i in range(self._rows) ];
        dimension = len(self._weights[0]);
        
        dim_max = [ float('-Inf') ] * dimension;
        dim_min = [ float('Inf') ] * dimension;
        
        for weight in self._weights:
            for index_dim in range(dimension):
                if (weight[index_dim] > dim_max[index_dim]):
                    dim_max[index_dim] = weight[index_dim];
                
                if (weight[index_dim] < dim_min[index_dim]):
                    dim_min[index_dim] = weight[index_dim];
        
        radius = [0.0] * len(self._weights[0]);
        for index_dim in range(dimension):
            radius[index_dim] = ( dim_max[index_dim] - dim_min[index_dim] ) / surface_divider;
        
        for point in self._data:
            for index_neuron in range(len(self)):
                point_covered = True;
                
                for index_dim in range(dimension):
                    if (abs(point[index_dim] - self._weights[index_neuron][index_dim]) > radius[index_dim]):
                        point_covered = False;
                        break;
                
                row = math.floor(index_neuron / self._cols);
                col = index_neuron - row * self._cols;
                
                if (point_covered is True):
                    density_matrix[row][col] += 1;
        
        return density_matrix;
    
    
    def show_winner_matrix(self):
        """!
        @brief Show winner matrix where each element corresponds to neuron and value represents
               amount of won objects from input dataspace at the last training iteration.
        
        @see show_distance_matrix()
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._award = wrapper.som_get_awards(self.__ccore_som_pointer);
        
        (fig, ax) = plt.subplots();
        winner_matrix = [ [0] * self._cols for i in range(self._rows) ];
        
        for i in range(self._rows):
            for j in range(self._cols):
                neuron_index = i * self._cols + j;
                
                winner_matrix[i][j] = self._award[neuron_index];
                ax.text(i, j, str(winner_matrix[i][j]), va='center', ha='center')
        
        ax.imshow(winner_matrix, cmap = plt.get_cmap('cool'), interpolation='none');
        ax.grid(True);
        
        plt.title("Winner Matrix");
        plt.show();
            
    
    def show_network(self, awards = False, belongs = False, coupling = True, dataset = True, marker_type = 'o'):
        """!
        @brief Shows neurons in the dimension of data.
        
        @param[in] awards (bool): If True - displays how many objects won each neuron.
        @param[in] belongs (bool): If True - marks each won object by according index of neuron-winner (only when dataset is displayed too).
        @param[in] coupling (bool): If True - displays connections between neurons (except case when function neighbor is used).
        @param[in] dataset (bool): If True - displays inputs data set.
        @param[in] marker_type (string): Defines marker that is used for dispaying neurons in the network.
        
        """
        
        if (self.__ccore_som_pointer is not None):
            self._size = wrapper.som_get_size(self.__ccore_som_pointer);
            self._weights = wrapper.som_get_weights(self.__ccore_som_pointer);
            self._neighbors = wrapper.som_get_neighbors(self.__ccore_som_pointer);
            self._award = wrapper.som_get_awards(self.__ccore_som_pointer);
        
        dimension = len(self._weights[0]);
        
        fig = plt.figure();
        axes = None;
        
        # Check for dimensions
        if ( (dimension == 1) or (dimension == 2) ):
            axes = fig.add_subplot(111);
        elif (dimension == 3):
            axes = fig.gca(projection='3d');
        else:
            raise NameError('Dwawer supports only 1D, 2D and 3D data representation');
        
        
        # Show data
        if (dataset == True):
            for x in self._data:
                if (dimension == 1):
                    axes.plot(x[0], 0.0, 'b|', ms = 30);
                    
                elif (dimension == 2):
                    axes.plot(x[0], x[1], 'b.');
                    
                elif (dimension == 3):
                    axes.scatter(x[0], x[1], x[2], c = 'b', marker = '.');                           
        
        # Show neurons
        for index in range(self._size):
            color = 'g';
            if (self._award[index] == 0): color = 'y';
            
            if (dimension == 1):
                axes.plot(self._weights[index][0], 0.0, color + marker_type);
                
                if (awards == True):
                    location = '{0}'.format(self._award[index]);
                    axes.text(self._weights[index][0], 0.0, location, color='black', fontsize = 10);                   
            
                if (belongs == True):
                    location = '{0}'.format(index);
                    axes.text(self._weights[index][0], 0.0, location, color='black', fontsize = 12);
                    for k in range(len(self._capture_objects[index])):
                        point = self._data[self._capture_objects[index][k]];
                        axes.text(point[0], 0.0, location, color='blue', fontsize = 10);
            
            if (dimension == 2):
                axes.plot(self._weights[index][0], self._weights[index][1], color + marker_type);
                
                if (awards == True):
                    location = '{0}'.format(self._award[index]);
                    axes.text(self._weights[index][0], self._weights[index][1], location, color='black', fontsize = 10);
                    
                if (belongs == True):
                    location = '{0}'.format(index);
                    axes.text(self._weights[index][0], self._weights[index][1], location, color='black', fontsize = 12);
                    for k in range(len(self._capture_objects[index])):
                        point = self._data[self._capture_objects[index][k]];
                        axes.text(point[0], point[1], location, color='blue', fontsize = 10);
                
                if ( (self._conn_type != type_conn.func_neighbor) and (coupling != False) ):
                    for neighbor in self._neighbors[index]:
                        if (neighbor > index):
                            axes.plot([self._weights[index][0], self._weights[neighbor][0]], [self._weights[index][1], self._weights[neighbor][1]], 'g', linewidth = 0.5);
            
            elif (dimension == 3):
                axes.scatter(self._weights[index][0], self._weights[index][1], self._weights[index][2], c = color, marker = marker_type);
                
                if ( (self._conn_type != type_conn.func_neighbor) and (coupling != False) ):
                    for neighbor in self._neighbors[index]:
                        if (neighbor > index):
                            axes.plot([self._weights[index][0], self._weights[neighbor][0]], [self._weights[index][1], self._weights[neighbor][1]], [self._weights[index][2], self._weights[neighbor][2]], 'g-', linewidth = 0.5);
                        
                
        plt.title("Network Structure");
        plt.grid();
        plt.show();