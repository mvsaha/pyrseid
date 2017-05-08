import sys
sys.dont_write_bytecode = True

from ..utils import date_to_doy
from ..product import BaseProduct
from ..file import BaseFile
from ..base import Range

import os
import datetime
import numpy as np


_valid_products_ = {'3B-HHR', '3B-HHR-E', '3B-HHR-L', '3B-MO'}
_real_time_products_ = {'3B-HHR-E', '3B-HHR-L'}
_short_names_ = {'HHR': 'HH', 'HHR-E': 'HHE', 'MO':'M', 'HHR-L':'HHL'}


def is_product_name(prod):
    '''Check if input string is a valid TRMM product name.'''
    if prod in _valid_products_:
        return True
    return False


class Product(BaseProduct):
    """A GPM data product."""
    
    def __init__(self, prodstr):
        """Build a IMERG Product."""
        if not is_product_name(prodstr):
            raise Exception("Invalid GPM product name: "+str(prodstr))
        
        self._is_realtime = prodstr in _real_time_products_
        
        sp = prodstr.split('-')
        level = sp[0]
        name = '-'.join(sp[1:])
        dr = Range(datetime.datetime(2014, 3, 12), None)
        version = 'V03E' if self.is_realtime else 'V03D'
        super().__init__(name=name, version=version, platform='GPM',
                         level=level, daterange=dr)
    
    @property
    def is_realtime(self):
        return self._is_realtime
    
    @property
    def satellite(self):
        return 'MRG'
    
    @property
    def datatype(self):
        return self.level
    
    @property
    def instrument(self):
        return 'MS'
    
    @property
    def algorithm(self):
        return '3IMERG'
    
    def is_final(self):
        """Is this a research quality product?"""
        return self.name not in _real_time_products_
    
    @property
    def shortname(self):
        return _short_names_[self.name]


_mo_base_url_ = ('http://gpm1.gesdisc.eosdis.nasa.gov/data/s4pa//'
                 '{}_L{}/{}_{}{}.{}/{}/{}')
_hhr_base_url_ = ('http://gpm1.gesdisc.eosdis.nasa.gov/data/s4pa//'
                  '{}_L{}/{}_{}{}.{}/{}/{}/{}')


_mo_base_url_ = ('http://gpm1.gesdisc.eosdis.nasa.gov/data/s4pa//'
                 '{}_L{}/{}_{}{}.{}/{}/{}')
_hhr_base_url_ = ('http://gpm1.gesdisc.eosdis.nasa.gov/data/s4pa//'
                  '{}_L{}/{}_{}{}.{}/{}/{}/{}')


class File(BaseFile):
    """An GPM file."""
    
    _fields = ('product', 'date')
    _is_deterministic = True  # We can deduce the filename from the requirments
    #_shape = (400, 1440)
    
    def __init__ (self, product, date):
        """Create a GPM File from a product and date requirement."""
        File.validate(product, date)
        self._product, self._date = product, date
    
    
    @staticmethod
    def determine(product, date):
        """Determine the path to a remote file."""
        if product is None or date is None:
            raise ValueError('Cannot determine file when any fields are None.')
        
        if product.name.startswith('HHR'):
            end_time = date + datetime.timedelta(minutes=29, seconds=59)
            end = "E{}{}59".format(str(end_time.hour).zfill(2),
                                   str(end_time.minute).zfill(2))
            sequence_indicator = str((date.hour * 60) + date.minute).zfill(4)
        
        elif product.name == 'MO':
            end = "E235959"
            sequence_indicator = str(date.month).zfill(2)
        
        else:
            raise NotImplementedError("Unknown GPM product.")
        
        day = "{}{}{}".format(str(date.year).zfill(4),
                              str(date.month).zfill(2),
                              str(date.day).zfill(2))
        
        start = "S{}{}00".format(str(date.hour).zfill(2),
                                 str(date.minute).zfill(2))
        
        fname = "{}-{}.{}.{}.{}.{}-{}-{}.{}.{}.HDF5".format(
            product.level, product.name, product.instrument,
            product.satellite,product.algorithm, day, start,
            end, sequence_indicator, product.version)
        
        
        if product.name.startswith('HHR'):
            doy = date_to_doy(date)
            return _hhr_base_url_.format(
                product.platform, product.level[0], product.platform,
                product.algorithm, product.shortname, product.level[0].zfill(2),
                date.year, str(doy).zfill(3), fname)

        elif product.name == 'MO':
            return _mo_base_url_.format(
                product.platform, product.level[0], product.platform,
                product.algorithm, product.shortname, product.level[0].zfill(2),
                date.year, fname)
        else:
            raise NotImplementedError("Don't know how to guess remote path.")
    
    
    @staticmethod
    def validate(product, date):
        """This function should raise an error if any fields are invalid."""
        if not type(product) is Product:
            raise TypeError('product must be a GPM product or None.')
        
        # Ensure we don't have an invalid date
        if not ((date is None) or (date in product.daterange)):
            raise ValueError('{} is not in the period of record for {}'.format(
                date, product))
        
        if date is None:
            return
        
        if product.name.startswith('HHR'):
            if not (date.minute % 30 == 0 and date.second == 0):
                raise ValueError('Input date must be an even 30-minute'
                    ' interval for half-hourly product {}.'.format(product))
        elif product.name == 'MO':
            if not (date.day == 1 and date.hour == 0 and date.minute==0 and date.second==0):
                raise ValueError('Input date must be the first of the'
                    '  month for the monthly product {}.'.format(product))
        else:
            raise ValueError('Cannot validate date for product {}'.format(product))
    
    
    @staticmethod
    def from_path(path, is_local=None):
        """Create a GPM File from an absolute path."""
        assert is_local in {None, True, False}
        
        if is_local is None:
            is_local = not path.startswith(('http://', 'ftp://'))
        
        if is_local:
            fname = path.split('/')[-1]
        else:
            fname = os.path.split(path)[-1]
        
        spl = fname.split('.')
        assert len(spl) is 8
        
        prodstr = spl[0]
        product = Product(prodstr)
        day, start, end = spl[4].split('-')
        date = datetime.datetime(int(day[:4]), int(day[4:6]), int(day[6:]),
                                 int(start[1:3]), int(start[3:5]))
        
        File.validate(product, date)
        
        f = File(product, date)
        f._path = path[:]
        f._is_valid = True
        f._is_local = is_local
        return f
    
    
    def __str__(self):
        return "File("+ str(self._product)+","+self._date.__repr__()+")"
    
    
    def __repr__(self):
        return str(self)
    
    
    def __hash__(self):
        return hash((self._product, self._date))


def have_files(folder,recursive=False):
    """List the valid TRMM files in a folder."""
    all_files = os.listdir(folder)
    gpm_files = []
    for f in all_files:
        try:
            tf = File.from_path(os.path.join(folder,f))
            gpm_files.append(tf)
        except:
            pass
    return gpm_files