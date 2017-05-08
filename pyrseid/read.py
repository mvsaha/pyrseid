"""
Reading data from hdfs
"""
import numpy as np
from .file import BaseFile


def fields_with_gdal(file):
    import gdal
    ds = gdal.Open(file.path)
    sds = ds.GetSubDatasets()
    del(ds)
    return sds


def fields_with_pyhdf(file):
    from pyhdf.SD import SD
    sds = SD(file.path)
    return list(sds.datasets())


def fields(file):
    """Find the name of sub-datasets contained in a file."""
    errors = [None, None, None]
    try:
        return fields_with_gdal(file)
    except Exception as gdal_error:
        errors[0] = gdal_error
    
    try:
        return fields_with_pyhdf(file)
    except Exception as pyhdf_error:
        errors[1] = pyhdf_error
       
    raise RuntimeError("Could not read data with either gdal or pyhdf backend. "
                       "Make sure one of these libraries is installed. The errors "
                       "given by each library are: \n"
                       "gdal:\n"
                       "   {}"
                       "pyhdf:\n"
                       "   {}\n".format(*errors))


def read_with_gdal(filename, field):
    #import gdal
    #fld = modis.fields(filename)[field_num][0]
    #ds = gdal.Open(fld)
    #data = ds.ReadAsArray()
    raise NotImplementedError


def read_with_pyhdf(filename, field):
    from pyhdf.SD import SD
    ds = SD(filename)
    data = ds.select(field)[:]
    ds.end()
    return data


def read_with_h5py(filename, field):
    import h5py
    ds = h5py.File(filename)
    data = ds[field][:]
    ds.close()
    return data


def read_hdf(file, field):
    """Read a file using either the gdal, pyhdf or h5py backend."""
    filename = file.path if issubclass(type(file), BaseFile) else file
    errors = [None, None, None]
    try:
        data = read_with_gdal(filename, field)
        return data
    except Exception as gdal_error:
        errors[0] = gdal_error
    
    try:
        data = read_with_pyhdf(filename, field)
        return data
    except Exception as pyhdf_error:
        errors[1] = pyhdf_error
    
    try:
        data = read_with_h5py(filename, field)
        return data
    except Exception as h5py_error:
        errors[2] = h5py_error
    
    raise RuntimeError(("Could not read data with either gdal or pyhdf backend. "
                       "Make sure one of these libraries is installed. The errors "
                       "given by each library are: \n"
                       "gdal:\n"
                       "   {}"
                       "pyhdf:\n"
                       "   {}\n"
                       "h5py:\n"
                       "   {}\n").format(*errors))


def read(file, field, fillfunc=None, fillval=np.nan, astype=None,
  correction_factor=None):
    """Read an data file as a numpy ndarray, with possible conversions.
    
    Requires GDAL or HDF4 support for hdf files.
    
    Parameters
    ----------
    f : modis.File
    field : str
        The sub-dataset within the file to read
    fillfunc : [None] | callable
        If supplied, this function must take a single numpy ndarray
        (the raw data) and return an identically sized boolean (logical)
        numpy ndarray. Where this array is True, the input data
        will be set to the fill value.
        
        Example, to set all -9999 values to np.nan:
            >>> fn = lambda: x == -9999 # The callable
            >>> read(f, field, fillfunc=fn, fillval=np.nan, astype=float)
    astype : [None] | int | float
        How to format the output data.
    correction_factor - [None] | float
            What to multiply the input dataset by after converting to
            return type.
    
    Returns
    -------
    data - numpy ndarray
    
    Notes
    -----
    The order of data processing is:
        [1] Apply fill_func to data (if it is supplied).
        [2] Convert data type, if supplied.
        [3] Multiply data by conversion factor
        [4] Fill the data with missing values (if fillfunc was supplied)
    
    This ordering permits you to identify fill values in the native format
    (like an equality comparison on an int array with a fill value, which
    could be problematic after converting to float), then convert to a
    desired type to fill (such as with np.nan, which is only valid in
    floating point data).
    """
    data = read_hdf(file, field)
    
    if fillfunc is not None:       #[1]
        to_fill = fillfunc(data)
    if astype is not None:
        data = data.astype(astype) #[2]
    if correction_factor is not None:
        data *= correction_factor
    if fillfunc is not None:       #[3]
        data[to_fill] = fillval
    
    return data