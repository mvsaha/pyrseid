import os
import numpy as np

from ..utils import pretty_lat_print, pretty_lon_print, path_is_local
from ..base import BoundingBox, Range
from ..tile import BaseTile
from ..product import BaseProduct
from ..file import BaseFile
from ..download import putfile

class Tile(BaseTile):
    """Represents a 10°x10° GFC granule."""
    
    _hrange = Range(0,35) # BaseTile needs this
    _vrange = Range(0,13)
    
    def __init__(self,v,h):
        """The granule to represent in (v,h) where (0,0) is the upper left granule"""
        super().__init__(v,h)
    
    
    def __repr__(self):
        """Format the print characteristics."""
        bbox = self.bbox()
        return 'GFC.Tile('+ pretty_lat_print(bbox.s) + '-' + \
                            pretty_lat_print(bbox.n) +', ' + \
                            pretty_lon_print(bbox.w) + '-' + \
                            pretty_lon_print(bbox.e) + ')'
    
    
    @staticmethod
    def that_contains(lat, lon):
        """Build a GFC Tile that contains a certain Point."""
        raise NotImplementedError
    
    
    @staticmethod
    def from_str(s):
        """Build a gfc.Tile from it's corresponding string specification.
        Ex.: 40N_080W"""
        
        def negate_SW(s):
            return -1 if s in ['S','W'] else 1
        
        try:
            la = negate_SW(s[2]) * int(s[:2])
            lo = negate_SW(s[7]) * int(s[4:7])
            v,h = int(8-(la/10)), int((lo/10)+18)
        except:
            raise ValueError('Ill-formed Tile specification string: "'+s+'"')
        
        return Tile(h=h,v=v)
    
    
    def bbox(self):
        """Return the bounding coordinates for a tile."""
        return BoundingBox(n=10*(8-self.v),s=10*(7-self.v),w=10*(self.h-18),e=10*(self.h-17))
    
    
    def grid(self):
        """Return the lat/lon coordinates for each pixel."""
        n = 10 * 60 * 60 # 1 arc-second for each pixel
        stride = 1/n # One pixel in degrees
        bb = self.bbox()
        lon = np.linspace(stride/2,10-(stride/2),n)
        lat = np.linspace(10-(stride/2),stride/2,n) # Reversed
        return {'lat':lat+bb.n,'lon':lon+bb.w}
    
    
    def __str__(self):
        """Generate a tile text specification."""
        bbox = self.bbox()
        lo = str(abs(int(bbox.w))).zfill(3) + ('W' if bbox.w<0 else 'E')
        la = str(abs(int(bbox.n))).zfill(2) + ('S' if bbox.n<0 else 'N')
        return la+'_'+lo


_valid_products_ = ['treecover2000','first','last','loss','gain','lossyear','datamask']
_valid_versions_ = [1.0,1.2]


def list_products(path=None):
    """List the GCF products in a directory, or all possible products if path is None."""
    if path is None:
        return _valid_products_[:]
    else:
        assert(os.path.isdir(path))
        return [l for l in os.listdir(path) if l.startswith(hansen_prefix)]


"""A GFC data product."""
class Product(BaseProduct):
    
    def __init__(self,product,version=1.2):
        """Build a GFC data product.
        
        Args:
            product: str
            version: [1.2] | 1.0
        """
        if type(product) is Product:
                self = product
        else:
            if version not in _valid_versions_:
                raise ValueError("Version {0} not supported".format(version))
            if product not in _valid_products_:
                raise ValueError("Not a valid GFC product.")
            else:
                super().__init__(name=product,version=version,platform="GFC")

                
_url_prefix='https://storage.googleapis.com/earthenginepartners-hansen'
_ver_str_ = {1.0:'GFC2013',1.2:'GFC2015'}
_ver_num_ = {'GFC2013':1.0,'GFC2015':1.2}
_hansen_ = 'Hansen_'


"""A Global Forest Cover file."""
class File(BaseFile):
    
    # Must define 'fields' for types that inherit from BaseFile
    _fields = ('product','tile')
    _is_deterministic = True # Override other BaseFile defaults
    _platform = 'GFC'
    
    def __init__(self,product,tile):
        """"""
        # set product
        try:
            assert(type(product)==Product or product is None)
            self._product = product
        except AssertionError:
            raise TypeError('product must be a valid gfc.Product or None')
        
        # set tile
        try:
            assert(type(tile)==Tile or tile is None)
            self._tile = tile
        except AssertionError:
            raise TypeError('tile must be a valid gfc.Tile or None')
        
        super().__init__(is_valid=True)
    
    
    @staticmethod
    def determine_file(product,tile):
        """Determine the path to another File .
        
        Arguments:
            d : [dict] - A dictionary whose keys are . Will raise
            an error if fields are not implemented.
        
        """
        fname = '_'.join([_hansen_+_ver_str_[product.version],product.name,str(tile)])+'.tif'
        return '/'.join([_url_prefix,_ver_str_[product.version],fname])
    
    
    def grab(self,directory,replace=False):
        """Download a file to a directory if it is not already there."""
        if not self.is_valid:
            raise RuntimeError('File is not valid: '+str(self))
        
        put_path = os.path.join(directory,self.filename)
        if not self.is_local and not os.path.exists(put_path):
            print("Downloading "+self.filename)
            putfile(self.path,put_path)
        
        if os.path.exists(put_path):
            # If this was successful, update self to point to the local version
            self._is_local = True
            self._path = put_path
    
    
    def __repr__(self):
        return 'GCF.File('+str(self.product)+', '+str(self.tile)+')'
    
    
    def read(self):
        """Read 
        TODO: Define a read object?"""
        import gdal
        if not self.is_local:
            raise RuntimeError("Can only read data from local (downloaded) Files.")
        return gdal.Open(self.path).ReadAsArray()
    
    
    @staticmethod
    def from_path(path):
        """Build a File from a path name."""
        # Ex: Hansen_GFC2015_treecover2000_40N_080W.tif
        f = File(None, None) # Build an invalid file
        try:
            split = os.path.split(path)[1].split('.')[0].split('_')
            tile = Tile.from_str('_'.join(split[3:5]))
            product = Product(split[2],_ver_num_[split[1]])
            f = File(product,tile)
            f._path = path
            f._is_valid = True
            
        except:
            f = File(None,None)
            f._path = path # invalid path
            f._is_valid = False
        
        f = File(prod, tile)
        f._path = path
        
        if path_is_local(path):
            f._is_local = True
        else:
            f._is_local = False
        
        return f
    
    def bbox(self):
        return self.tile
    
def have_files():
    for i in range(0):
        pass
    
    
def read(file):
    import gdal
    tif = gdal.Open(file.path).ReadAsArray()

