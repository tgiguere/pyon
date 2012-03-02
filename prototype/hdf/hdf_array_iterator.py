#!/usr/bin/env python

'''
@package ion.services.dm.ingestion
@file ion/services/dm/inventory/hdf_array_iterator.py
@author Swarbhanu Chatterjee
@brief HDFArrayIterator. Used in replay. Accepts a certain number of hdf files. Extracts the arrays out of them. Uses the ArrayIterator to
resize the arrays into blocks that are of the right size so that they do not have to be read into memory.
'''

from operator import mul
from pyon.core.exception import NotFound, BadRequest
from pyon.public import log


def acquire_data( hdf_files = None, var_names=None, concatenate_block_size = None, bounds = None):

    import h5py, numpy

    arrays_out = {}

    # Note: stop_index is exclusive
    if bounds:
        start_index, stop_index = bounds
        num_entries_to_read = stop_index - start_index
    else:
        start_index = 0
        num_entries_to_read = None

    # the default dataset names that are going to be used for input...
    default_var_names = ['temperature', 'conductivity', 'salinity', 'pressure']

    assert hdf_files, NotFound('No hdf_files provided to extract data from!')

    def check_for_dataset(nodes, var_names):
        """
        A function to check for datasets in an hdf file and collect them
        """

        import h5py

        for node in nodes:

            if isinstance(node, h5py._hl.dataset.Dataset):

                #-------------------------------------------------------------------------------------------------------
                # if the name of the dataset (without grp/subgrp name) is one of the supplied variable names of interest,
                # update the dictionary for relevant datasets
                #-------------------------------------------------------------------------------------------------------

                dataset_name = node.name.rsplit('/', 1)[1]
                dataset = node

                if dataset_name in var_names:
                    dict_of_h5py_datasets[dataset_name] = dataset

            elif isinstance( node , h5py._hl.group.Group):
                check_for_dataset(node.values())


    for hdf_file in hdf_files:

        #-------------------------------------------------------------------------------------------------------
        # refresh the h5py dataset list
        #-------------------------------------------------------------------------------------------------------

        dict_of_h5py_datasets = {}

        log.debug('Reading file: %s' % hdf_file)

        #-------------------------------------------------------------------------------------------------------
        # make a file object
        #-------------------------------------------------------------------------------------------------------

        file = h5py.File(hdf_file,'r')

        #-------------------------------------------------------------------------------------------------------
        # get the list of groups or datasets if there are no groups in the file
        #-------------------------------------------------------------------------------------------------------

        nodes = file.values()

        if var_names is None:
            var_names = default_var_names

        #-------------------------------------------------------------------------------------------------------
        # checking for datasets in the hdf file whose names appear in the list of variable names supplied
        #-------------------------------------------------------------------------------------------------------

        check_for_dataset(nodes, var_names)
        log.debug('dict_of_h5py_datasets: %s' % dict_of_h5py_datasets)

        #-------------------------------------------------------------------------------------------------------
        # if no relevant dataset was found in the hdf file, then skip that file
        #-------------------------------------------------------------------------------------------------------

        if not dict_of_h5py_datasets:
            continue


        #-------------------------------------------------------------------------------------------------------
        # Iterate over the supplied variable names
        #-------------------------------------------------------------------------------------------------------

        for vn in var_names:

            #-------------------------------------------------------------------------------------------------------
            # fetch the dataset
            #-------------------------------------------------------------------------------------------------------

            dataset = dict_of_h5py_datasets.get(vn, None)

            #-------------------------------------------------------------------------------------------------------
            # if this variable is not in a dataset in the hdf file, skip this variable name for this hdf file
            #-------------------------------------------------------------------------------------------------------

            if not dataset:
                continue

            #-------------------------------------------------------------------------------------------------------
            # if the array in the dataset is too small, grab the whole array
            #-------------------------------------------------------------------------------------------------------

            if dataset.value.size < concatenate_block_size:

                # grab the whole array in the dataset
                d = dataset.value
                # update the arrays_out dict
                arrays_out[vn] = d

                out_dict = {'variable_name' : vn,
                            'current_slice' :  (slice(0,dataset.value.size)), # this is the whole array
                            'range' : (numpy.nanmin(d), numpy.nanmax(d)),
                            'current_array_chunk' : d,
                            'arrays_out_dict' : arrays_out,
                            'concatenated_array' : d,
                            'flush_out_array' : None
                }

                yield out_dict

            else:

                #--------------------------------------------------------------------------------------------------------------
                #
                # Calling the ArrayIterator to slice the array held by the dataset and yield the bits
                #
                # feeding in the slice_ that is expected in ArrayIterator....this should read in all the values in the dataset
                #--------------------------------------------------------------------------------------------------------------


                if num_entries_to_read:
                    log.warn("came here!")
                    arri = ArrayIterator(dataset, concatenate_block_size)[( slice(start_index,min(dataset.value.size, num_entries_to_read)) )]
                else:
                    arri = ArrayIterator(dataset, concatenate_block_size)[(slice(start_index, dataset.value.size))]

                for d in arri:

                    read_entries = d.size
                    if num_entries_to_read:
                        left_to_read_entries = num_entries_to_read - read_entries

                    rng = (numpy.nanmin(d), numpy.nanmax(d))

                    if concatenate_block_size:

                        if vn in arrays_out:
                            if arrays_out[vn].size < concatenate_block_size:
                                arrays_out[vn] = numpy.concatenate((arrays_out[vn], d), axis = 0)
                            else:
                                indices_left = concatenate_block_size - arrays_out[vn].size

                                arrays_out[vn] = numpy.concatenate((arrays_out[vn], d[:indices_left]), axis = 0)

                                flush_out_array = d[indices_left:]

                                #-----------------------------------------------------------------------------------------
                                # yields variable_name, the current slice, range, the sliced data,
                                # the dictionary holding the concatenated arrays by variable name
                                #-----------------------------------------------------------------------------------------

                                log.warn('size of array[%s]: %s' % (vn,arrays_out[vn].size))

                                out_dict = {'variable_name' : vn,
                                            'current_slice' : arri.curr_slice,
                                            'range' : rng,
                                            'current_array_chunk' : d,
                                            'arrays_out_dict' : arrays_out,
                                            'concatenated_array' : arrays_out[vn],
                                            'flush_out_array' : flush_out_array
                                }

                                yield out_dict

                                arrays_out[vn] = flush_out_array
                        else:
                            arrays_out[vn] = d

                    # if no concatenate_block_size is provided
                    else:

                        #-----------------------------------------------------------------------------------------
                        # to have the same yielded values as when the concatenate_block_size
                        # is provided, we need to make sure that an empty dictionary goes out for arrays_out
                        # and the arrays_out[vn] values are None

                        # its good to keep the same interface and that is why we are yielding the same
                        # number of output parameters for all cases of concatenate_block_size
                        #-----------------------------------------------------------------------------------------

                        out_dict = {'variable_name' : vn,
                                    'current_slice' : arri.curr_slice,
                                    'range' : rng,
                                    'current_array_chunk' : d,
                                    'arrays_out_dict' : None,
                                    'concatenated_array' : None,
                                    'flush_out_array' : None
                        }

                        yield out_dict



#----------------------------------------------------------------------------------------------------------------------------
# Copied below ArrayIterator class written by Chris Mueller since eoi-services has not yet been included in my repositories
#----------------------------------------------------------------------------------------------------------------------------


class ArrayIterator(object):
    """
    Buffered iterator for big arrays.

    This class creates a buffered iterator for reading big arrays in small
    contiguous blocks. The class is useful for objects stored in the
    filesystem. It allows iteration over the object *without* reading
    everything in memory; instead, small blocks are read and iterated over.

    The class can be used with any object that supports multidimensional
    slices, like variables from Scientific.IO.NetCDF, pynetcdf and ndarrays.

    """

    def __init__(self, var, buf_size=None):
        self.var = var
        self.buf_size = buf_size

        self.start = [0 for dim in var.shape]
        self.stop = [dim for dim in var.shape]
        self.step = [1 for dim in var.shape]

    def __getitem__(self, index):
        """
        Return a new arrayterator.

        """
        # Fix index, handling ellipsis and incomplete slices.
        if not isinstance(index, tuple): index = (index,)
        fixed = []
        length, dims = len(index), len(self.shape)
        for slice_ in index:
            if slice_ is Ellipsis:
                fixed.extend([slice(None)] * (dims-length+1))
                length = len(fixed)
            elif isinstance(slice_, (int, long)):
                fixed.append(slice(slice_, slice_+1, 1))
            else:
                fixed.append(slice_)
        index = tuple(fixed)
        if len(index) < dims:
            index += (slice(None),) * (dims-len(index))

        # Return a new arrayterator object.
        out = self.__class__(self.var, self.buf_size)
        for i, (start, stop, step, slice_) in enumerate(
            zip(self.start, self.stop, self.step, index)):

            log.debug('type of out: %s' % type(out))
            log.debug('slice_: %s' % str(slice_))

            out.start[i] = start + (slice_.start or 0)
            out.step[i] = step * (slice_.step or 1)
            out.stop[i] = start + (slice_.stop or stop-start)
            out.stop[i] = min(stop, out.stop[i])
        return out

    @property
    def __array_interface__(self):
        slice_ = tuple(slice(*t) for t in zip(
            self.start, self.stop, self.step))
        data = self.var[slice_].copy()
        return {
            'version': 3,
            'shape': self.shape,
            'typestr': data.dtype.str,
            'data': data,
            }

    @property
    def flat(self):
        for block in self:
            for value in block.flat:
                yield value

    @property
    def shape(self):
        return tuple(max(0, ((stop-start-1)//step+1))
        for start, stop, step in
        zip(self.start, self.stop, self.step))

    def __iter__(self):
        # Skip arrays with degenerate dimensions
        if [dim for dim in self.shape if dim <= 0]:
            log.warn("StopIteration called because of degernate dimensions")
            raise StopIteration

        start = self.start[:]
        stop = self.stop[:]
        step = self.step[:]
        ndims = len(self.var.shape)

        while 1:
            count = self.buf_size or reduce(mul, self.shape)

            # iterate over each dimension, looking for the
            # running dimension (ie, the dimension along which
            # the blocks will be built from)
            rundim = 0
            for i in range(ndims-1, -1, -1):
            # if count is zero we ran out of elements to read
                # along higher dimensions, so we read only a single position
                if count == 0:
                    stop[i] = start[i]+1
                elif count <= self.shape[i]:  # limit along this dimension
                    stop[i] = start[i] + count*step[i]
                    rundim = i
                else:
                    stop[i] = self.stop[i]  # read everything along this dimension
                stop[i] = min(self.stop[i], stop[i])
                count = count//self.shape[i]

            # yield a block
            slice_ = tuple(slice(*t) for t in zip(start, stop, step))
            self.curr_slice = slice_
            yield self.var[slice_]

            # If this is a scalar variable, bail out
            if ndims == 0:
                log.warn("StopIteration called because ndims is 0")
                raise StopIteration

            # Update start position, taking care of overflow to other dimensions
            start[rundim] = stop[rundim]  # start where we stopped
            for i in range(ndims-1, 0, -1):
                if start[i] >= self.stop[i]:
                    start[i] = self.start[i]
                    start[i-1] += self.step[i-1]
            if start[0] >= self.stop[0]:
                log.warn("StopIteration called because array was exhausted")
                raise StopIteration