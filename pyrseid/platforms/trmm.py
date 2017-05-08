import sys
sys.dont_write_bytecode = True

import geospatial
import geospatial as gs
import geospatial.utils as gu
from geospatial.utils import date_to_doy
from geospatial.product import BaseProduct
from geospatial.file import BaseFile
from geospatial import Range
from ..utils import list_files

import os
import datetime
import numpy as np
import calendar
import re


_valid_products_ = ['3B42','3B42_daily','3B43']


def is_product_name(prod):
    '''Check if input string is a valid TRMM product name.'''
    if prod in _valid_products_:
        return True
    else:
        return False


class Product(BaseProduct):
    """A TRMM data product."""
    
    def __init__(self,product,version=7):
        """Build a TRMM file from a requirement."""
        if not is_product_name(product):
            raise Exception("Invalid TRMM Product name: {}".format(product))
        
        if version is 6:
            dr = Range(datetime.datetime(1998, 1, 1),
                       datetime.datetime(2011, 6, 30))
        elif version is 7:
            dr = Range(datetime.datetime(1998, 1, 1),
                       datetime.datetime(2020, 7, 31))

        super().__init__(name=product, version=version, platform='TRMM',
                         level=int(product[0]), daterange=dr)


def trmm_3B4X_doy(d):
    """Year and DOY string, with midnight evaluating to the preceding day.
    This is needed because of the way in which the files are stored online
    (00Z being classified as the previous day)
    """
    if d.hour is 0:
        d -= datetime.timedelta(days=1)
    return str(d.year).zfill(4),  str(date_to_doy(d)).zfill(3)


_base_ftp_ = '://disc2.nascom.nasa.gov/data/s4pa'
_base_http_ = '://disc2.nascom.nasa.gov/s4pa'
TRMM_ = 'TRMM_'

_7A_bounds_ = Range(datetime.datetime(2000,1,1),datetime.datetime(2010,9,30))
_6A_start_ = datetime.datetime(2007,5,1)



class File(BaseFile):
    """A TRMM file."""
    
    _fields = ('product', 'date')
    _is_deterministic = True
    _platform = 'TRMM'
    _shape = (400, 1440)
    
    def __init__ (self, product, date):
        """Create a TRMM File from a product and date requirement.

        Arguments
        ---------
        product - TRMM.Product
        date    - datetime.date(time)
        """
        try:
            assert type(product)==Product or product is None
            self._product = product
        except AssertionError:
            raise TypeError('product must be a valid trmm.Product or None')
        
        try:
            assert issubclass(type(date), datetime.date) or date is None
            date = datetime.datetime.fromordinal(date.toordinal())
            self._date = date
        except AssertionError:
            raise TypeError('date must be a datetime.date[time] or None')

        if not date in product.daterange:
            raise ValueError("{} is out of daterange {} for {}.".format(
                    date, product._daterange, product))

        super().__init__()  # This calls 'determine_file()'


    @staticmethod
    def determine(product, date, protocol='http'):
        """Determine the path to a File with given criteria.

        Arguments
        ---------
        product : trmm.Product
        date : datetime.datetime
        protocol : ['http'] | ['ftp']
        
        Notes
        -----
        Only Level 3 products are supported (and assumed).
        """
        if protocol=='http':
            base = _base_http_
        elif protocol=='ftp':
            base = _base_ftp_
        else:
            raise ValueError("protocol must be 'http' or 'ftp'.")

        yr, mo = str(date.year).zfill(4), str(date.month).zfill(2)
        dy = str(date.day).zfill(2)
        roll_yr, roll_doy = trmm_3B4X_doy(date)
        roll_yr_short = roll_yr

        level = 'L'+str(product.level) # 'L1','L2' or 'L3'
        ver = str(product.version)
        prod = product.name

        if product.name == '3B42':
            if product.version == 6:
                prod += '.6'
                yr = yr[2:]
                hr = str(date.hour)
                if date >= _6A_start_:
                    ver += 'A'

            elif product.version == 7:
                if date in _7A_bounds_:
                    ver += 'A'
                hr = str(date.hour).zfill(2)

            fname = '.'.join([product.name,yr+mo+dy,hr,ver,'HDF.Z'])
            return '/'.join([protocol+base,TRMM_+level,TRMM_+prod,roll_yr,roll_doy,fname])

        elif product.name == '3B42_daily':
            if product.version == 6:
                prod += '.6'

            fname = '.'.join([product.name,yr,mo,dy,ver,'bin'])
            return '/'.join([protocol+base,TRMM_+level,TRMM_+prod,roll_yr,roll_doy,fname])

        elif product.name == '3B43':
            if product.version == 6:
                prod += '.6'
                short_yr = yr[2:]
                if date >= _6A_start_:
                    ver += 'A'

            elif product.version == 7:
                short_yr = yr
                if date in _7A_bounds_:
                    ver += 'A'

            doy = str(date_to_doy(date))
            fname = '.'.join([product.name,short_yr+mo+dy,ver,'HDF'])

        return '/'.join([protocol+base,TRMM_+level,TRMM_+prod,yr,doy.zfill(3),fname])


    @staticmethod
    def from_path(path):
        """Create a TRMM File from a absolute path."""

        if path.startswith(('http','ftp')):
            loc, fname = False, path.split('/')[-1]
        else:
            loc, fname = True, os.path.split(path)[-1]

        spl = fname.split('.')
        prod = spl[0]

        def guess_century(dstr):
            if len(dstr) is 6: # We have the short year convention
                if int(dstr[:2]) > 98:
                    dstr = '19'+dstr
                else:
                    dstr = '20'+dstr
            return dstr

        if prod == '3B42':
            dstr = guess_century(spl[1])
            date = datetime.datetime(int(dstr[:4]), int(dstr[4:6]),
                                     int(dstr[6:]), int(spl[2][:2]))
            ver = int(spl[3][0])

        elif prod == '3B42_daily':
            dstrs = spl[1:4]
            date = datetime.datetime(int(dstrs[0]), int(dstrs[1]), int(dstrs[2]))
            ver = int(spl[4][0])

        elif prod == '3B43':
            dstr = guess_century(spl[1])
            date = datetime.datetime(int(dstr[:4]), int(dstr[4:6]), int(dstr[6:]))
            ver = int(spl[2][0])
        else:
            raise ValueError('prod str "{}" is not supported'.format(prod))
        
        f = File(Product(prod, version=ver), date=date)
        f._path = path[:]
        f._is_valid = True
        f._is_local = True
        return f


    def __str__(self):
        return "File("+ str(self._product)+","+self._date.__repr__()+")"


    def __repr__(self):
        return str(self)


    def __hash__(self):
        return hash((self._product, self._date))


    def __gt__(self, other):
        if type(other) is not type(self):
            raise TypeError("unorderable types: {0} < {1}",type(self),type(other))
        else:
            return self.date > other.date


    def read(self,remove_unzipped=True):
        """Read a TRMM file into an numpy ndarray."""
        assert(self.is_local is True)

        # Read in different filetypes
        if self.extension == 'bin':
            data = self.read_bin()
        elif self.extension == 'hdf':
            data = self.read_hdf()
        elif self.extension == 'z':
            self.unzip() # Get the unzipped version

        # Go from hourly rates to total mm
        if self.product.name == '3B42':
            data *= 3.0
        elif self.product.name == '3B42_daily':
            data *= 1.0
        elif self.product.name == '3B43':
            data *= hours_in_month(self.date.year,self.date.month)

        # Set missing data
        data[data < 0] = np.nan
        return data

    def read_bin(self):
        """Only call this if this File has a .bin extension."""
        t = np.flipud(np.fromfile(self.path, dtype=np.float32,
                      count=np.prod(self.shape)).byteswap().reshape(self.shape))
        shift = self.shape[1] / 2 # Shift this into TRMM reference (lon:[-180,180])

        # Doing it this way because `np.roll` wants to convert 'float64'->'int64'
        #t = np.roll(t,shift,axis=1,dtype='float32')

        t = np.hstack([t[:, shift:], t[:, :shift]])

        t[t < 0] = np.nan  # Negative rainfall values are invalid
        return t

    def read_hdf(self):
        import gdal
        h = gdal.Open('HDF4_SDS:UNKNOWN:"'+self.path+'":0')
        if h is None:
            raise Exception('Could not read the specified file.')
        return np.rot90(h.ReadAsArray())

    def read_zipped_hdf(self):
        raise NotImplementedError('Uh oh.')
    
    def local_dir(self, top_level_dir):
        """Find appropriate location for this File under a top level
        directory."""
        if self.product.name in {'3B42',}:
            return os.path.join(top_level_dir, self.product.name, str(self.date))
        return os.path.join(top_level_dir, self.product.name, str(self.date.year))
    
    def unzip(self):
        raise NotImplementedError('Cannot unzip compressed HDF.')


def is_trmm_datestr(s):
    '''Check if the datestring matches the standard TRMM format.'''
    if not len(s) == 8:
        return False
    try:
        y = int(s[:4])
        m = int(s[4:6])
        d = int(s[6:])
        return datetime.datetime(y, m, d)
    except:
        return False


def files_in_folder(folder,recursive=False):
    """List the valid TRMM files in a folder, in chronological order."""
    all_files = list_files(folder, recursive=recursive)
    trmm_files = []
    for f in all_files:
        try:
            tf = File.from_path(f)
            trmm_files.append(tf)
        except:
            pass
    return sorted([f for f in trmm_files if f.is_valid], key=lambda x: x.date)


def have_files(toppath, prod, dates=None, hours=None):
    """List matching local TRMM files."""
    files = files_in_folder(os.path.join(toppath,prod.name), recursive=True)
    matching_files = []
    
    for f in files:
        if dates is None or f.date in dates:
            if hours is None:
                matching_files.append(f)
            elif f.date.hour in hours:
                matching_files.append(f)
    
    return matching_files


def which_pixel(coord):
    """Determine which TRMM pixel a geographic coordinate falls into."""
    if coord.lat>=50 or coord.lat <= -50:
        raise ValueError('Coordinate lat='+str(coord.lat)+' out of bounds.')
    elif coord.lon>180 or coord.lon < -180:
        raise ValueError('Coordinate lon is out of bounds [-180,180]')
    ypix = int(np.rint((-coord.lat+49.875) / 0.25))
    xpix = int(np.rint((coord.lon+179.875) / 0.25))
    return (ypix,xpix)


def hours_in_month(year,month):
    '''Return the number of hours in a month.'''
    return calendar.monthrange(year,month)[1]* 24


def read(f,negs=None):
    '''Read a TRMM file into an numpy ndarray.'''
    h = gdal.Open('HDF4_SDS:UNKNOWN:"'+f.fullpath()+'":0')
    if h is None:
        raise Exception('Could not read the specified file.')

    #print(hours_in_month(f._date.year,f._date.month))
    if str(f._prod) == '3B42':
        data = np.rot90(h.ReadAsArray()) * 3.0
    elif str(f._prod) == '3B43':
        data = np.rot90(h.ReadAsArray()) * hours_in_month(f._date.year,f._date.month)
    else:
        raise Exception('Unknown product')

    if negs is not None:
        data[data<0] = negs

    return data


def shape():
    '''Return the shape of the TRMM domain.'''
    return (400,1440)


def bbox(y,x):
    '''Calculate a bounding box for a trmm pixel.'''
    latmax = -((y * 0.25) - 49.75)
    latmin = latmax - 0.25
    lonmax = (x * 0.25) - 178
    lonmin = lonmax - 0.25
    return (latmin,lonmin,latmax,lonmax)


def grid():
    """Find the geographic coordinates of the TRMM domain.
    
    Returns
    -------
    A dict with keys 'lat' and 'lon', each with shape (400,1440).
    """
    nlon = 1440
    nlat = 400
    xs = 0.25
    ys = -0.25
    x0 = -180. + (xs/2.)
    y0 = 50. + (ys/2.)
    lons = xs * np.arange(nlon) + x0
    lats = ys * np.arange(nlat) + y0
    lons,lats = np.meshgrid(lons, lats)
    return {'lat':lats, 'lon':lons}


def _lon_row():
    nlon = 1440
    xs = 0.25
    x0 = -180. + (xs/2.)
    lons = xs * np.arange(nlon) + x0
    return lons


def LST_offset():
    raise NotImplementedError
    # return a 400x1440 numpy array of timedeltas reflecting how
    # Local Standard Time differs from UTC (the TRMM timestamp)
    lons = _lon_row() # We only need the first row
    offset_hrs = (lons/180.0) * 12
    to_timedelta = np.vectorize(lambda h: datetime.timedelta(hours=h))
    timeoffset = to_timedelta(offset_hrs)
    return timeoffset


def read_bin(path, shape, shift=True):
    """Only call this if this File has a .bin extension."""
    t = np.flipud(np.fromfile(path, dtype=np.float32,
                  count=np.prod(shape)).byteswap().reshape(shape))
    if shift is True:
        nshift = shape[1] / 2  # Shift this into TRMM reference (lon:[-180,180])
        # Doing it this way because np.roll wants to convert float64 to int64
        # t = np.roll(t,shift,axis=1, dtype='float32')
        t = np.hstack([t[:, nshift:], t[:, :nshift]])
    t[t < 0] = np.nan  # Negative rainfall values are invalid
    return t
