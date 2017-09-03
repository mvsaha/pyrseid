import os
import numpy as np

from ...base import Range
from ...download import ftp_login, ftp_listdir
from ...product import BaseProduct
from ...tile import BaseTile
from ...file import BaseFile
from ...utils import doy_to_datetime, date_to_psv, list_links, ensure_dir_exists
from collections import namedtuple


def list_valid_products():
    """Query USGS server for available MODIS products."""
    base_url = "http://e4ftl01.cr.usgs.gov/"
    valid_products = []
    sats = {"MOTA": "MCD", "MOLT": "MOD", "MOLA": "MYD"}
    
    for s in sats:
        links = list_links('/'.join([base_url, s]))
        valid_products.extend(
            [l.strip('/') for l in links if l.startswith(sats[s])])
    return valid_products


_this_dir_ = os.path.dirname(__file__)
# _this_dir_ = %pwd #  For jupyter
# Run this code once when the package is imported

_prod_file = open(os.path.join(_this_dir_, 'modis_products.txt'))
_prod_list = [i for i in _prod_file.read().split('\n') if len(i)]
_prod_file.close()


# def update_products_list():
#     file_name = 'modis_products.txt'
#
#     vp = list_valid_products()
#
#     if os.path.exists(file_name):
#         print('EXISTS')
#         os.remove(file_name)
#
#     with open(file_name, mode='x') as file:
#         file.writelines('\n'.join(vp))


def is_valid_product(prod):
    """Is the input string a valid modis.Product identifier.

    Must include version number:
        GOOD:
            'MCD43A3.005'
        BAD:
            'MCD43A3'
    """
    if prod in _prod_list or isinstance(prod, Product):
        return True
    else:
        return False


_satellite_names_ = {'MCD': 'Combined', 'MOD': 'Terra', 'MYD': 'Aqua'}
_satellites_ = {"MCD": "MOTA", "MYD": "MOLA", "MOD": "MOLT"}


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


def get_product_folder(modfolder, product):
    return os.path.join(modfolder, '.'.join([product.name, product.version]))


HVPair = namedtuple('HVPair', ['h', 'v'], )


class Tile(BaseTile):
    _hrange = Range(0, 35)
    _vrange = Range(0, 17)
    
    def __init__(self, h=None, v=None):
        super().__init__(v=v, h=h)
    
    @staticmethod
    def from_str(tilestr):
        """Create a MODIS tile from a tile text string."""
        if len(tilestr) is not 6 or tilestr[0] is not 'h' or tilestr[
            3] is not 'v':
            raise ValueError("Invalid MODIS Tile text specification: '{}'"
                             .format(tilestr))
        return Tile(h=int(tilestr[1:3]), v=int(tilestr[4:6]))
    
    def __str__(self):
        return 'h' + str(self.h).zfill(2) + 'v' + str(self.v).zfill(2)
    
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
        rlat = lat * (np.pi / 180.0)  # In radians
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
        if modfolder is None:
            if self.is_local:
                return os.path.split(self.path)[0]
            else:
                raise ValueError("must input modfolder for non-local Files.")
        else:
            return os.path.join(get_product_folder(modfolder, self.product),
                                date_to_psv(self.date))