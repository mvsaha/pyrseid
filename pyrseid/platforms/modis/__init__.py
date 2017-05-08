import sys
sys.dont_write_bytecode = True
import datetime
import os
import urllib
import textwrap
import re
import math
import numpy as np

from ...base import Range
from ...download import ftp_login, ftp_listdir
from ...file import BaseFile
from ...product import BaseProduct
from ...read import read_hdf
from ...tile import BaseTile
from ...utils import doy_to_datetime, date_to_psv, list_links, ensure_dir_exists


def list_valid_products():
    """Query USGS server for available MODIS products."""
    base_url = "http://e4ftl01.cr.usgs.gov/"
    valid_products = []
    sats = {"MOTA":"MCD", "MOLT":"MOD", "MOLA":"MYD"}
    
    for s in sats:
        links = list_links('/'.join([base_url,s]))
        valid_products.extend([l.strip('/') for l in links if l.startswith(sats[s])])
    return valid_products


_this_dir_ = os.path.dirname(__file__)
#_this_dir_ = %pwd #  For jupyter
# Run this code once when the package is imported

_prod_file = open(os.path.join(_this_dir_, 'modis_products.txt'))
_prod_list = [i for i in _prod_file.read().split('\n') if len(i)]
_prod_file.close()


def is_valid_product(prod):
    '''Is the input string a valid modis.Product identifier.

    Must include version number:
        GOOD:
            'MCD43A3.005'
        BAD:
            'MCD43A3'
    '''
    if prod in _prod_list or isinstance(prod,Product):
        return True
    else:
        return False


_satellite_names_ = {'MCD':'Combined', 'MOD':'Terra', 'MYD':'Aqua'}
_satellites_ = {"MCD":"MOTA", "MYD":"MOLA", "MOD":"MOLT"}

class Product(BaseProduct):
    """A MODIS product and version."""
    def __init__(self, prodstr):
        if not is_valid_product(prodstr):
            raise Exception("Invalid MODIS Product name:", prodstr)
        
        name, version = prodstr.split('.')
        
        super().__init__(name=name, version=version, platform='MODIS',
                         level=3)
    
    @property
    def satellite(self):
        return _satellites_[self.name[:3]]
    
    @property
    def satellite_name(self):
        """The """
        return _satellite_names_[self.name[:3]]
    
    @property
    def sat(self):
        """The 3-letter abbreviation of the MODIS satellite."""
        return self.name[:3]


from collections import namedtuple
HVPair = namedtuple('HVPair', ['h', 'v'], )

class Tile(BaseTile):
    _hrange = Range(0,35)
    _vrange = Range(0,17)
    
    
    def __init__(self,h=None,v=None):
        super().__init__(v=v,h=h)
    
    
    @staticmethod
    def from_str(tilestr):
        """Create a MODIS tile from a tile text string."""
        if len(tilestr) is not 6 or tilestr[0] is not 'h' or tilestr[3] is not 'v':
            raise ValueError("Invalid MODIS Tile text specification: '{}'"
              .format(tilestr))
        return Tile(h=int(tilestr[1:3]), v=int(tilestr[4:6]))
    
    
    def __str__(self):
        return 'h'+str(self.h).zfill(2)+'v'+str(self.v).zfill(2)
    
    
    def __repr__(self):
        return "modis.Tile(" + self.__str__() + ")"
    
    
    @staticmethod
    def from_coord(lat, lon):
        """Build a Tile that contains a coordinate."""
        h, v = Tile.locate(lat, lon)
        return Tile(h=int(h), v=int(v))
    
    
    def locate(lat, lon):
        """Return the (h,v) indices of a coordinate."""
        lat, lon = np.array(lat), np.array(lon)
        lat_per_tile = 180. / 18.
        v = ((-lat + 90) // lat_per_tile).astype(int)
        rlat = lat * (np.pi / 180.0) # In radians
        h = (((lon * np.cos(rlat)) + 180) // 10).astype(int)
        if v.size == 1 and v.size > 1:
            ret_v = np.empty_like(h)
            ret_v[:] = int(v)
        else:
            ret_v = v
        
        return HVPair(h, ret_v)


class File(BaseFile):
    """A MODIS level 3 File."""
    
    _fields = ('product', 'date', 'tile')
    _is_deterministic = False
    
    def __init__(self, product, date, tile):
        File.validate(product, date, tile)
        self._product, self._date, self._tile = product, date, tile
    
    
    @staticmethod
    def from_path(path):
        is_local = not path.startswith(('http://', 'ftp://'))
        if not is_local:
            fname = path.split('/')[-1]
        else:
            fname = os.path.split(path)[-1]
        
        spl = fname.split('.')
        assert len(spl) is 6
        product = Product('.'.join((spl[0], spl[3])))
        dstr = spl[1]
        yr, doy = int(dstr[1:5]), int(dstr[5:8])
        date = doy_to_datetime(yr, doy)
        tile = Tile.from_str(spl[2])
        
        File.validate(product, date, tile)
        f = File(product, date, tile)
        f._path = path[:]  # Want a copy
        f._is_valid = True
        f._is_local = is_local
        return f
    
    
    @staticmethod
    def validate(product, date, tile):
        """Raise an error if the inputs are invalid."""
        pass
    
    
    def local_dir(self, modfolder=None):
        """Return the local directory where this file should reside.
        given a top-level modfolder. If this file already exists 
        locally, then this returns the actual directory
        """
        if self.is_local and modfolder is None:
            return os.path.split(self.path)[0]
        else:
            return os.path.join(get_product_folder(modfolder, self.product),
                                date_to_psv(self.date))

def available_dates(prod, dates=None, server="lpdaac"):
    if server == 'lpdaac':
        import geospatial.platforms.modis.lpdaac as lpdaac
        return lpdaac.available_dates(prod, dates=dates)
    elif server == 'ladsweb':
        import geospatial.platforms.modis.ladsweb as ladsweb
        return ladsweb.available_dates(prod, dates=dates)


def available_files(prod, dates=None, tiles=None, exact_dates=False,
                    server="lpdaac"):
    if server == 'lpdaac':
        import geospatial.platforms.modis.lpdaac as lpdaac 
        return lpdaac.available_files(prod, dates=dates, tiles=tiles,
                                      exact_dates=exact_dates)
    elif server == 'ladsweb':
        import geospatial.platforms.modis.ladsweb as ladsweb
        return ladsweb.available_files(prod, dates=dates, tiles=tiles)


def get_product_folder(modfolder, product):
    return os.path.join(modfolder, '.'.join([product.name, product.version]))


def have_product_folder(modfolder, product):
    return os.path.exists(get_product_folder(modfolder, product))


def have_date_folders(modfolder, prod, dates=None):
    """List the date folders that exsit locally for a modis.Product"""
    pf = get_product_folder(modfolder, prod)
    df = dict()
    if not os.path.isdir(pf):
        return df
    poss_df = os.listdir(pf)
    for pdf in poss_df:
        try:
            sp = pdf.split('.')
            assert len(sp) is 3
            y,m,d = int(sp[0]), int(sp[1]), int(sp[2])
            
            date = datetime.datetime(y, m, d)
            if dates is not None and date not in dates:
                continue
            df[date] = os.path.join(pf, pdf)
        except:
            pass
    return df


def have_files(modfolder, prod, dates=None, tiles=None):
    """List the MODIS files that product, date and tile specification.
    Arguments:
        modfolder - str
            The top level MODIS directory exists.
        
        prod - modis.Product
            A valid MODIS product object
        
        dates - [None] | sequence(datetime.datetime) | Range(datetime.datetime)
            A list or Range of datetimes to match against. A local file with
            date ```d``` will only be returned if ```d in dates``` is True.
            If dates is None (the default) then Files with all dates will be
            returned.
            
        tiles - [None] | TileRange(modis.Tile) | sequence(modis.Tile):
            A list of Range of MODIS Tiles to match against. A local file with
            tile ```t``` will only be returned if ```t in tiles``` is True.
            If tiles is None (the default) then Files with all tiles will be 
            returned.
    
    Returns:
        files - list(modis.Files)
            The list of local modis.Files that have product prod, and whose date
            and tiles match input arguments.
    """
    files = []
    
    if not os.path.isdir(get_product_folder(modfolder, prod)):
        return []
    
    date_folders = have_date_folders(modfolder, prod, dates=dates)
    for d, df in date_folders.items():
        poss_file_paths = os.listdir(df)
        
        for pf in poss_file_paths:
            try:
                if pf == ".modlist":
                    continue
                
                path = os.path.join(df, pf)
                #print(path)
                f = File.from_path(path)

                if dates is not None and f.date not in dates:
                    continue

                if tiles is not None and f.tile not in tiles:
                    continue
                files.append(f)
            except:
                pass
            
    files.sort(key=lambda x: x.date)
    return files


def date_to_psv(date):
    return "{}.{}.{}".format(str(date.year).zfill(4),
                             str(date.month).zfill(2), 
                             str(date.day).zfill(2))


def grab_files(files, modfolder, replace=False):
    """Download a list of files into a MODIS library."""
    
    # These files must all have the same product (they can have diff dates)
    assert all(f.product == files[0].product for f in files)
    
    # Make sure all of the date folders exist or create them
    product_folder = get_product_folder(modfolder, files[0].product)
    unique_dates = set(f.date for f in files)
    date_folders = {d: os.path.join(product_folder, date_to_psv(d))
                    for d in unique_dates}
    
    for d, df in date_folders.items():
        ensure_dir_exists(df)
    
    # Loop through these files and put them in 
    for f in files:
        f.grab(date_folders[f.date], replace=replace)
    
    return files


def grab_all(modfolder, product, dates=None, tiles=None, replace=False):
    af = available_files(product, dates=dates, tiles=tiles)
    
    # Make sure all of the date folders exist or create them
    product_folder = get_product_folder(modfolder, product)
    unique_dates = set(f.date for f in af)
    date_folders = {d: os.path.join(product_folder, date_to_psv(d))
                    for d in unique_dates}
    
    for d, df in date_folders.items():
        ensure_dir_exists(df)
    
    # Loop through these files and put them in 
    for f in af:
        f.grab(date_folders[f.date], replace=replace)
    return af


def locate(lat,lon, resolution=None):
    '''Get the MODIS Tile and pixel of a geographic coordinate.'''
    if abs(lat) > 90:
        raise Exception("Latitude out of bounds")
    elif abs(lon) > 180 :
        raise Exception("Longitude out of bounds")

    yn1to1 = -lat/90
    xn1to1 = lon/180
    
    xn1to1_adj = xn1to1 * math.cos(yn1to1*math.pi/2)
    
    # Find the bounding tile
    hfrac = ((xn1to1_adj+1)/2)*36
    h = math.floor(hfrac)
    if h == 36:
        h = 35

    vfrac = ((yn1to1+1)/2)*18
    v = math.floor(vfrac)
    if v == 18:
        v = 17
    
    tile = Tile(h=h,v=v)
    
    # Now compute the fractional component:
    return tile,(vfrac-v,hfrac-h)


def grid(tile, resolution):
    """Geographic coordinates for each pixel in a MODIS tile

    Arguments:
        tile - modis.Tile object
        resolution - 1200 | 2400 | 4800
            Corresponding to 1 km, 500 m or 250 m nominal pixel size.
    
    Returns
        A dict with two fields: 'lat' and 'lon'. Each are numpy.ndarrays
        with [resolution x resolution] dimensions.
    """
    start, end = 1/(resolution*2), 1-(1/(resolution*2))
    lat_start = ((18 - tile.v - start) * 10) - 90
    lat_end = ((18 - tile.v - end) * 10) - 90
    lats = np.linspace(lat_start, lat_end, resolution)[...,None]
    x = ((np.linspace(tile.h + start, tile.h + end, resolution) / 18.) - 1)[None,...]
    lons = 180. * x / np.sin(np.pi*-(lats-90)/180)
    lats = np.tile(lats,resolution)
    return {'lat': lats, 'lon': lons}


def offset(tile, resolution):
    """Pixel offset from the top left of the MODIS SIN grid."""
    return tile.v * resolution, tile.h * resolution


def latitude(y_pix, resolution, tile=None):
    """Find the latitude of MODIS pixels.
    
    Pixels refer to elements of an image in the MODIS SINUSOIDAL
    projection.
    
    Arguments:
        y_pix - numpy array
            Vertical location of a MODIS pixel.
        
        resolution - 1200 | 2400 | 4800
            Number of elements in each MODIS image.
        
        tile - [None] | modis.Tile
            If tile is specified, then y_pix should be given as pixels
            relative to the upper left corner of tile offset (see offset).
    
    Returns:
        lat - numpy array
            Latitude of the input pixels.
    """
    if tile is not None:
        y_off, x_off = offset(tile, resolution)
        y_pix = y_pix + y_off
    lat_per_pixel = 180 / (18 * resolution) # Degrees lat in each vertical pixel
    lat = (y_pix * -lat_per_pixel) + (90 - (lat_per_pixel / 2))
    lat[lat>90] = np.nan
    lat[lat<-90] = np.nan
    return lat


def longitude(y_pix, x_pix, resolution, tile=None):
    """Find the longitude of MODIS pixels.
    
    Pixels refer to elements of an image in the MODIS SINUSOIDAL
    projection.
    
    Arguments:
        y_pix - numpy array
            Vertical location of a MODIS pixel.
        
        x_pix - numpy array
            Horizontal location of a MODIS pixel. Must be the same
            size as y_pix
        
        resolution - 1200 | 2400 | 4800
            Number of elements in each MODIS image.
        
        tile - [None] | modis.Tile
            If tile is specified, then y_pix and x_pix should
            be given as pixels relative to the upper left corner
            of tile offset (see offset).
    
    Returns:
        lon - numpy array
            Longitude of the input pixels. Will have the same
            shape as y_pix and x_pix
    """
    if tile is not None:
        y_off, x_off = offset(tile, resolution)
        y_pix, x_pix = y_pix + y_off, x_pix + x_off
    
    y_radians_per_pixel = np.pi / (18 * resolution) # Degrees lat in each vertical pixel
    
    # Radians from 0 @ North Pole to PI @ South Pole
    y_rad = (y_pix * y_radians_per_pixel) + (y_radians_per_pixel / 2)
    
    lon_per_pixel = 360 / (36 * resolution)
    lon = (x_pix * lon_per_pixel) + (-180 + (lon_per_pixel / 2))
    lon /= np.sin(y_rad)
    lon[lon>180] = np.nan
    lon[lon<-180] = np.nan
    return lon
    

def latlon(y_pix, x_pix, resolution, tile=None):
    lat = latitude(y_pix, resolution, tile)
    return {'lat':lat,
            'lon':longitude(y_pix, x_pix, resolution=resolution, tile=tile)}


def read(f, field, fillfunc=None, fillval=np.nan, astype=None, correction_factor=None):
    """Read a MODIS File as a numpy ndarray.
    [REQUIRES GDAL AND HDF4 SUPPORT]

    PARAMETERS:
        f - modis.File
        
        field_num - The position of the subdataset in the 
            The number of the SubDataSet to read in.
        
        fill - [None] | dict
            If fill is specified, it should be a dict with of the form:
                
                {callable,value}
            
            Callable should be a function that takes a single numpy ndarray
            (the raw data) and returns an identically sized boolean (logical)
            numpy ndarray. Where this array is True, the input data will be set
            to the fill value.
            
            Example, to set all -9999 values to np.nan:
            >>> find_9999 = lambda: x == -9999 # The callable
            >>> modis.read(f,field,fill={find_9999:np.nan})
        
        astype - [int] | float
            How to format the output data.
        
        correction_factor - [None] | float
            What to multiply the input dataset by after converting to return type.
    
    RETURNS:
        data - numpy ndarray
    
    NOTES: The order of data processing is:
        [1] Apply fill callable to data (if it exists).
        [2] Convert data to astype
        [3] Fill the data with

        This ordering permits you to identify fill values in the native format
        (like an equality comparison on an int array, which would be dangerous
        after converting to float), then convert to a desired type to fill
        (such as with np.nan, which is only valid in float numpy arrays).
    """
    if type(f) is File:
        f = f.path
    
    data = read_hdf(f, field)
    
    if fillfunc is not None:           #[1]
        to_fill = fillfunc(data)
    
    if astype is not None:
        data = data.astype(astype)     #[2]
    
    if correction_factor is not None:
        data *= correction_factor
    
    if fillfunc is not None:           #[3]
        data[to_fill] = fillval
    
    return data


def make_list(x):
    try:
        x.__iter__()
        return list(x)
    except:
        return [x]


def assemble(u, d, func=None, fill=np.nan, dtype=float, depth=1):
    """Arrange multiple, identically sized, 2-d arrays into one.

    PARAMETERS:
        u - (int, int)
            "Unit shape." The size of one component.

        d - dict((v, h):data)
            A dict where the key is the spatial coordinate of the image chunk
            and the value is the data for spatial chunk.

                Should have the form {(y,x):data}

            The (y,x) integer coordinates tell us how to arrange the data in the
            final 2d grid. If func is not specified, each data entry should be
            a numpy ndarray with a shape u. If func is specified, then
            the result of the func when applied to each data value
            (i.e. func(data)) should have the shape u (but each datum
            need not have this shape).
        
        dtype - int | float
            The type of the array.

        func - [None] | callable
            Optional function to apply to each value of d. If this is
            specified then the result should have the dimensions u when
            applied to each value of the dict d.s

        fill - [np.nan] | numeric
            Fill values for tiles that are not present. Default is np.nan

        depth - [1] | positive int
            Number of bands of each component array.

    RETURNS:
        A numpy ndarray of the assembled tiles.

    EXAMPLE:
    [1]>>> res = 1200
    [2]>>> hv = ((19,10),(20,10),(20,11))
    [3]>>> d = {(v,h):modis.Tile(h=h,v=v) for h,v in hv}
    [4]>>> func = lambda x: modis.grid(x,resolution=res)['lat']
    [5]>>> modlats = modis.assemble((res,res),d,func)

    Explanation:
        In the first line, we set the length of the side of each square chunk.
    In line [2] we specify the Tiles we want to assemble, in this case 3 tiles
    over Africa. In line [3] we put each of these Tiles in as data into a dict
    with their granule coordinate (y,x) as a key. Note that this is relative
    ordering and it does not have to start out at (y,x)=(0,0). In line [4] we
    define the func that will expand every data value (a Tile) in d into a numpy
    ndarray, the result of which is required to have shape u.
        The result is a 2400x2400 modlats contains latitudes for the three input
    Tiles. The output will have shape (2400,2400). The lower-left Tile (19,11)
    is not part of the input, and so it is set to the fill value, which defaults
    to NaN.

    A schematic of the final assembly:
     _____________
    |      |      |
    |h19v10|h20v10|  <- Latitude values stitched together.
    |______|______|
    |//////|      |
    |/FILL/|h20v11|
    |//////|______|
     
    """
    y, x = zip(*d)
    ymin, ymax = min(y), max(y)
    xmin, xmax = min(x), max(x)

    Y, X = u[0]*(ymax + 1 - ymin), u[1]*(xmax + 1 - xmin)

    if depth is 1:
        assembled = np.zeros(shape=[Y, X], dtype=dtype)
    else:
        assembled = np.zeros(shape=make_list(depth) + [Y, X], dtype=dtype)
    
    assembled[:] = fill
    
    for iy in range(ymin, ymax+1):
        for ix in range(xmin, xmax+1):
            _y_, _x_ = iy-ymin, ix-xmin
            if (iy, ix) in d:
                if func is None:
                    assembled[...,
                              u[0]*_y_:u[0]*(_y_+1),
                              u[1]*_x_:u[1]*(_x_+1)] = d[(iy, ix)]
                else:
                    assembled[...,
                              u[0]*_y_:u[0]*(_y_+1),
                              u[1]*_x_:u[1]*(_x_+1)] = func(d[(iy, ix)])
    return assembled
