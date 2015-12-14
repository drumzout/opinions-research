# -*- coding: utf-8 -*-
# pylint: disable=E1101

'''
Helper functions
'''
from __future__ import division, print_function

import numpy as np
import numpy.random as rand
import networkx as nx
import json
import os

from numpy.linalg import inv
from datetime import datetime


def rowStochastic(A):
    '''Makes a matrix row (right) stochastic.

    Given a real square matrix, returns a new matrix which is right
    stochastic, meaning that each of its rows sums to 1.

    Args:
        A (NxN numpy array): The matrix to be converted

    Returns:
        A NxN numpy array which is row stochastic.
    '''

    return A / A.sum(axis=1, keepdims=True)


def randomSpanningTree(N, rand_weights=False):
    '''Creats a graph of N nodes connected by a random spanning tree.

    Args:
        N (int): Number of nodes

    Returns:
        A NxN numpy array representing the adjacency matrix of the graph.

    '''

    nodes = rand.permutation(N)
    A = np.zeros((N, N))

    for i in xrange(1, N):
        w = rand.random() if rand_weights else 1
        A[nodes[i - 1], nodes[i]] = w
        A[nodes[i], nodes[i - 1]] = w

    return A


def meanDegree(A):
    '''Calculates the mean degree of a graph.

    Args:
        A (NxN numpy array): The adjacency matrix of the graph

    Returns:
        The mean degree of the graph.

    '''
    B = np.empty_like(A)
    np.copyto(B, A)
    B[B > 0] = 1
    degrees = B.sum(axis=1)
    return np.mean(degrees)


def cluster_count(x, eps=0.1):
    '''Calculates the number of clusters in HK-type models.

    The function creates a histogram from the given vector and returns
    the number of bins that contain a non-trivial percentage of the values.
    For normal runs of HK models, this is equal to the number of the clusters.

    We have determined that len(x)/10 seems to be a good number for the
    initial number of bins. If you encouter errors, you might want to
    experiment with it.

    Args:
        x (1xN numpy array): The input vector

        eps (float): The threshold for accepting a bin. If the bin contains
        more than eps * (size of largest bin) values, then we count it as
        a cluster.

    Returns:
        The number of clusters.
    '''
    if (len(x.shape) > 1):
        raise ValueError('Please provide a 1-D numpy array')
    bins, _ = np.histogram(x, bins=len(x)/10)
    cluster_bins = bins > eps * bins.max()
    return np.sum(cluster_bins)


def gnp(N, p, rand_weights=False, verbose=True):
    '''Constructs an connected undirected  G(N, p) network with random weights.

    To ensure connectivity, we begin by creating a random spanning tree on the
    nodes. Afterwards we proceed by adding nodes like we would on a classic
    Erdos-Renyi network.

    Args:
        N (int): Number of nodes

        p (double): The probability that each vertice is created

        rand_weights (bool): Weights are random numbers in (0, 1) instead of
        binary. In that case the matrix is also normalized to become
        row-stochastic (default: false)

        verbose (bool): Choose whether to print the size and the mean
        degree of the network

    Returns:
        A NxN numpy array representing the adjacency matrix of the graph.

    '''

    A = randomSpanningTree(N)
    for i in xrange(N):
        for j in xrange(N):
            r = rand.random()
            if r < p:
                w = rand.random() if rand_weights else 1
                A[i, j] = w
                A[j, i] = w

    if verbose:
        print('G(N,p) Network Created: N = {N}, Mean Degree = {deg}'.format(
              N=N, deg=meanDegree(A)))

    if rand_weights:
        A = rowStochastic(A)

    return A


def barabasi_albert(N, M, seed, verbose=True):
    '''Create random graph using Barabási-Albert preferential attachment model.

    A graph of N nodes is grown by attaching new nodes each with M edges that
    are preferentially attached to existing nodes with high degree.

    Args:
        N (int):Number of nodes

        M (int):Number of edges to attach from a new node to existing nodes

        seed (int) Seed for random number generator

    Returns:
        The NxN adjacency matrix of the network as a numpy array.

    '''

    A_nx = nx.barabasi_albert_graph(N, M, seed=seed)
    A = nx.adjacency_matrix(A_nx).toarray()

    if verbose:
        print('Barbasi-Albert Network Created: N = {N}, '
              'Mean Degree = {deg}'.format(N=N, deg=meanDegree(A)))

    return A


def from_edgelist(path, delimiter=' '):
    '''Read a graph from an edgelist like those provided by Stanford's snap.

    An edgelist is a simple text file in which each line contains the ids of
    two nodes connected by an edge.

    Args:
        path (string): The path of the edgelist file.

        delimiter (string): The string used to separate values. Default is
        whitespace.

    Returns:
        A, N where A is the NxN Adjacency matrix of the graph and N is the
        number of nodes

    '''
    if not os.path.isfile(path):
        raise NameError
    G = nx.read_edgelist(path, delimiter=delimiter, nodetype=int)
    A = nx.adjacency_matrix(G).toarray()
    N = A.shape[0]
    return A, N


def expected_equilibrium(A, s):
    '''Calculates the equilibrium of the Friedkin-Johnsen Model

    Args:
        A (NxN numpy array): Adjacency matrix (its diagonal is the stubborness)

        s (1xN numpy array): Intrinsic beliefs vector

    Returns:
        ((I-A)^-1)Bs

    '''

    N = np.shape(A)[0]
    B = np.diag(np.diag(A))

    return np.dot(np.dot(inv(np.eye(N) - (A - B)), B), s)


def saveModelData(simid, **kwargs):
    '''Save the initial conditions and the results of a simulation

    Args:
        simid (string): Unique simulation id starting with the name
        of the model and followed by a unique number

        **kwargs: Important data of the simulation that need to be saved.
        Those depend on the model but generally should contain the initial
        opinions, the opinions over time, the adjacency matrix etc. The names
        of the files are determined by the name of each dictionary entry so
        try to keep these consistent. Numpy arrays get a file of their own.
        If the type of the element does not have type numpy.ndarray then it is
        added to a common json formatted metadata file instead.

    '''

    # Create results directory and cd into it
    if not os.path.isdir('results'):
        os.mkdir('./results')
        print('Created /results directory')
    #os.chdir('./results')

    print('Saving simulation data [{0}]'.format(simid))

    # Various non-essential info about the simulation
    metadata = {'datetime': str(datetime.now())}

    # Check if data with the same name already exists
    if os.path.isfile('{0}_metadata.txt'.format(simid)):
        print('Files for simulation {0} already exist. Will'.format(simid),
              'append "_duplicate" string to results. Please change file'
              'names by hand.')
        simid += '_duplicate'

    # Save the arrays used in the simulation
    for name, data in kwargs.iteritems():
        if type(data) == np.ndarray:
            np.savetxt('./results/{simid}_{name}.txt'.format(simid=simid, name=name),
                       data, fmt='%6.4f')
        else:
            metadata[name] = data

    with open('./results/{0}_metadata.txt'.format(simid), 'w') as metadata_file:
        json.dump(metadata, metadata_file, indent=4)
