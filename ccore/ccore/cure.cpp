/**************************************************************************************************************

Cluster analysis algorithm: CURE

Based on article description:
 - S.Guha, R.Rastogi, K.Shim. CURE: An Efficient Clustering Algorithm for Large Databases. 1998.

Copyright (C) 2015    Andrei Novikov (pyclustering@yandex.ru)

pyclustering is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyclustering is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

**************************************************************************************************************/

#include "cure.h"
#include "support.h"

#include <limits>
#include <set>


cure_cluster::cure_cluster(void) : closest(nullptr), distance_closest(0), mean(nullptr) {
	points = new std::vector< std::vector<double> * >();
	rep = new std::vector< std::vector<double> * >();
}


cure_cluster::cure_cluster(std::vector<double> * point) : closest(nullptr), distance_closest(0) {
	mean = new std::vector<double>(point->size(), 0);

	points = new std::vector< std::vector<double> * >(1, point);
	rep = new std::vector< std::vector<double> * >(1, point);

	std::copy(point->begin(), point->end(), mean->begin());
}


cure_cluster::~cure_cluster() {
	if (mean != nullptr) {
		delete mean;
		mean = nullptr;
	}

	delete points;	/* only storage, we are not owners of points */
	points = nullptr;

	delete rep;		/* only storage, we are not owners of points */
	rep = nullptr;
}


cure_queue::cure_queue(void) {
	queue = new std::list<cure_cluster *>();
	tree = new kdtree();
}


cure_queue::cure_queue(const std::vector< std::vector<double> > * data) {
	queue = new std::list<cure_cluster *>();
	create_queue(data);

	tree = new kdtree();

	for (cure_queue::const_iterator cluster = queue->begin(); cluster != queue->end(); cluster++) {
		for (std::vector<std::vector<double> *>::const_iterator point = (*cluster)->rep->begin(); point != (*cluster)->rep->end(); point++) {
			tree->insert(*point, *cluster);
		}
	}
}


cure_queue::~cure_queue() {
	if (queue != nullptr) {
		for (std::list<cure_cluster *>::iterator cluster = queue->begin(); cluster != queue->end(); cluster++) {
			delete *cluster;
			*cluster = nullptr;
		}

		delete queue;
		queue = nullptr;
	}

	if (tree != nullptr) {
		delete tree;
		tree = nullptr;
	}
}


void cure_queue::create_queue(const std::vector< std::vector<double> > * data) {
	for (std::vector< std::vector<double> >::const_iterator iter = data->begin(); iter != data->end(); iter++) {
		cure_cluster * cluster = new cure_cluster((std::vector<double> *) &(*iter));
		queue->push_back(cluster);
	}

	for (std::list<cure_cluster *>::iterator first_cluster = queue->begin(); first_cluster != queue->end(); first_cluster++) {
		double minimal_distance = std::numeric_limits<double>::max();
		cure_cluster * closest_cluster = nullptr;

		for (std::list<cure_cluster *>::iterator second_cluster = queue->begin(); second_cluster != queue->end(); second_cluster++) {
			if (*first_cluster != *second_cluster) {
				double dist = get_distance(*first_cluster, *second_cluster);
				if (dist < minimal_distance) {
					minimal_distance = dist;
					closest_cluster = *second_cluster;
				}
			}
		}

		(*first_cluster)->closest = closest_cluster;
		(*first_cluster)->distance_closest = minimal_distance;
	}

	auto distance_comparison = [](cure_cluster * cluster1, cure_cluster * cluster2) { return cluster1->distance_closest < cluster2->distance_closest; };
	queue->sort(distance_comparison);
}


double cure_queue::get_distance(cure_cluster * cluster1, cure_cluster * cluster2) {
	double distance = std::numeric_limits<double>::max();
	for (std::vector<std::vector<double> *>::const_iterator point1 = cluster1->rep->begin(); point1 != cluster1->rep->end(); point1++) {
		for (std::vector<std::vector<double> *>::const_iterator point2 = cluster2->rep->begin(); point2 != cluster2->rep->end(); point2++) {
			double candidate_distance = euclidean_distance(*point1, *point2);
			if (candidate_distance < distance) {
				distance = candidate_distance;
			}
		}
	}

	return distance;
}


void cure_queue::merge(cure_cluster * cluster1, cure_cluster * cluster2, const unsigned int number_repr_points, const double compression) {
	remove_representative_points(cluster1);
	remove_representative_points(cluster2);

	queue->remove(cluster1);
	queue->remove(cluster2);

	cure_cluster * merged_cluster = new cure_cluster();
	merged_cluster->insert_points(cluster1->points);
	merged_cluster->insert_points(cluster2->points);

	merged_cluster->mean = new std::vector<double>((*cluster1->points)[0]->size(), 0);
	for (unsigned int dimension = 0; dimension < merged_cluster->mean->size(); dimension++) {
		(*merged_cluster->mean)[dimension] = (cluster1->points->size() * (*cluster1->mean)[dimension] + cluster2->points->size() * (*cluster2->mean)[dimension]) / (cluster1->points->size() + cluster2->points->size());
	}

	std::set<std::vector<double> *> * temporary = new std::set<std::vector<double> *>();
	
	for (unsigned int index = 0; index < number_repr_points; index++) {
		double maximal_distance = 0;
		std::vector<double> * maximal_point = nullptr;

		for (std::vector<std::vector<double> *>::const_iterator point = merged_cluster->points->begin(); point != merged_cluster->points->end(); point++) {
			double minimal_distance = 0;
			if (index == 0) {
				minimal_distance = euclidean_distance(*point, merged_cluster->mean);
			}
			else {
				minimal_distance = euclidean_distance(*point, (*temporary->begin()));
			}

			if (minimal_distance >= maximal_distance) {
				maximal_distance = minimal_distance;
				maximal_point = *point;
			}
		}

		if (temporary->find(maximal_point) == temporary->end()) {
			temporary->insert(maximal_point);
		}
	}

	for (std::set<std::vector<double> *>::iterator point = temporary->begin(); point != temporary->end(); point++) {
		std::vector<double> * representative_point = new std::vector<double>((*point)->size(), 0);
		for (unsigned int index = 0; index < (*point)->size(); index++) {
			(*representative_point)[index] = (*(*point))[index] + compression * ( (*merged_cluster->mean)[index] - (*(*point))[index] );
		}

		merged_cluster->rep->push_back(representative_point);
	}

	delete temporary;
	temporary = nullptr;

	insert_representative_points(merged_cluster);

	std::list<cure_cluster *> * relocation_request = nullptr;

	if (queue->size() > 0) {
		merged_cluster->closest = *(queue->begin());
		merged_cluster->distance_closest = get_distance(merged_cluster, merged_cluster->closest);

		/* relocation request */
		relocation_request = new std::list<cure_cluster *>();

		for (cure_queue::iterator cluster = queue->begin(); cluster != queue->end(); cluster++) {
			double distance = get_distance(merged_cluster, *cluster);

			/* Check if distance between new cluster and current is the best than now. */
			if (distance < merged_cluster->distance_closest) {
				merged_cluster->closest = *cluster;
				merged_cluster->distance_closest = distance;
			}

			/* Check if current cluster has removed neighbor. */
			if ( ((*cluster)->closest == cluster1) || ((*cluster)->closest == cluster2) ) {
				/* If previous distance was less then distance to new cluster then nearest cluster should be found in the tree. */
				if ((*cluster)->distance_closest < distance) {
					cure_cluster * nearest_cluster = nullptr;
					double nearest_distance = std::numeric_limits<double>::max();

					for (std::vector<std::vector<double> * >::iterator point = (*cluster)->rep->begin(); point != (*cluster)->rep->end(); point++) {
						kdtree_searcher searcher(*point, tree->get_root(), distance);

						std::vector<double> * nearest_node_distances = new std::vector<double>();
						std::vector<kdnode *> * nearest_nodes = searcher.find_nearest_nodes(nearest_node_distances);

						for (unsigned int index = 0; index < nearest_nodes->size(); index++) {
							if ( ((*nearest_node_distances)[index] < nearest_distance) && ( (*nearest_nodes)[index]->get_payload() != (*cluster) ) ) {
								nearest_distance = (*nearest_node_distances)[index];
								nearest_cluster = (cure_cluster *) (*nearest_nodes)[index]->get_payload();
							}
						}

						delete nearest_nodes;
						delete nearest_node_distances;
					}

					if (nearest_cluster == nullptr) {
						(*cluster)->closest = merged_cluster;
						(*cluster)->distance_closest = distance;
					}
					else {
						(*cluster)->closest = nearest_cluster;
						(*cluster)->distance_closest = nearest_distance;
					}
				}
				else {
					(*cluster)->closest = merged_cluster;
					(*cluster)->distance_closest = distance;
				}

				relocation_request->push_back((*cluster));
			}
		}
	}

	delete cluster1; cluster1 = nullptr;
	delete cluster2; cluster2 = nullptr;

	/* insert merged cluster */
	insert_cluster(merged_cluster);

	/* relocate requested clusters */
	if (relocation_request != nullptr) {
		for (cure_queue::iterator cluster = relocation_request->begin(); cluster != relocation_request->end(); cluster++) {
			remove_cluster(*cluster);
			insert_cluster(*cluster);
		}

		delete relocation_request;
		relocation_request = nullptr;
	}
}


void cure_queue::insert_cluster(cure_cluster * inserted_cluster) {
	for (cure_queue::iterator cluster = queue->begin(); cluster != queue->end(); cluster++) {
		if ( inserted_cluster->distance_closest < (*cluster)->distance_closest ) {
			queue->insert(cluster, inserted_cluster);
			return;
		}
	}

	queue->push_back(inserted_cluster);
}


void cure_queue::remove_representative_points(cure_cluster * cluster) {
	for (std::vector<std::vector<double> *>::const_iterator point = cluster->rep->begin(); point != cluster->rep->end(); point++) {
		tree->remove(*point);
	}
}


void cure_queue::insert_representative_points(cure_cluster * cluster) {
	for (std::vector<std::vector<double> *>::iterator point = cluster->rep->begin(); point != cluster->rep->end(); point++) {
		tree->insert(*point, cluster);
	}
}


cure::cure(const std::vector< std::vector<double> > * sample, const unsigned int clusters_number, const unsigned int points_number, const double level_compression) {
	data = (std::vector< std::vector<double> > *) sample;

	number_points = points_number;
	number_clusters = clusters_number;
	compression = level_compression;

	queue = new cure_queue(sample);
}


cure::~cure() {
	if (clusters != nullptr) {
		for (std::vector<std::vector<unsigned int> *>::const_iterator iter = clusters->begin(); iter != clusters->end(); iter++) {
			delete (*iter);
		}

		delete clusters;
		clusters = nullptr;
	}

	if (queue != nullptr) {
		delete queue;
		queue = nullptr;
	}
}


void cure::process() {
	unsigned int allocated_clusters = queue->size();
	while(allocated_clusters > number_clusters) {
		cure_cluster * cluster1 = *(queue->begin());
		cure_cluster * cluster2 = cluster1->closest;

		/* merge new cluster using these clusters */
		queue->merge(cluster1, cluster2, number_points, compression);

		allocated_clusters = queue->size();
	}

	/* prepare stardard representation of clusters */
	clusters = new std::vector<std::vector<unsigned int> *>();
	for (cure_queue::const_iterator cluster = queue->begin(); cluster != queue->end(); cluster++) {
		std::vector<unsigned int> * standard_cluster = new std::vector<unsigned int>();
		for (std::vector<std::vector<double> * >::const_iterator point = (*cluster)->points->begin(); point != (*cluster)->points->end(); point++) {
			unsigned int index_point = (unsigned int) (*point - &(*(data->begin())));
			standard_cluster->push_back(index_point);
		}

		clusters->push_back(standard_cluster);
	}

	delete queue;
	queue = nullptr;
}
