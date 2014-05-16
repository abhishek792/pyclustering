import unittest;

from gcolor.hysteresis import hysteresisgcolor;

from support.graph import read_graph;

from samples.definitions import GRAPH_SIMPLE_SAMPLES;

class Test(unittest.TestCase):
    def templateTestColoring(self, filename, alpha, eps, steps, time):
        graph = read_graph(filename);
        network = hysteresisgcolor(graph.data, alpha, eps);
        
        (t, dyn) = network.simulate(steps, time);
        map_coloring = network.get_map_coloring(0.05);
        
        # Check number of colors
        assigned_colors = set(map_coloring);
        
        # Check validity of color numbers
        for color_number in range(0, len(assigned_colors), 1):
            assert color_number in assigned_colors;
            
        # Check validity of colors
        for index_node in range(len(graph.data)):
            color_neighbors = [ map_coloring[index] for index in range(len(graph.data[index_node])) if graph.data[index_node][index] != 0 and index_node != index];
            #print(index_node, map_coloring[index_node], color_neighbors, assigned_colors, map_coloring, "\n\n");
            assert map_coloring[index_node] not in color_neighbors;        


    def testColoringSimple1(self):
        self.templateTestColoring(GRAPH_SIMPLE_SAMPLES.GRAPH_SIMPLE1, 1.2, 1.8, 2000, 20);
        
    def testColoringCircle2(self):
        self.templateTestColoring(GRAPH_SIMPLE_SAMPLES.GRAPH_ONE_CIRCLE2, 1.1, 1.1, 2000, 20);
        
    def testColoringFivePointedFrameStar(self):
        self.templateTestColoring(GRAPH_SIMPLE_SAMPLES.GRAPH_FIVE_POINTED_FRAME_STAR, 1, 1, 3000, 30);


if __name__ == "__main__":
    unittest.main();