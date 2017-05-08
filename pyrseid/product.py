"""
Class representing a remote sensing product.
"""
from .base import Range


"""Base class for platfrom specific data products."""
class BaseProduct:
    
    def __init__(self, name=None, version=None, platform=None,
                 level=None, daterange=Range(None, None)):
        self._name = name
        self._version = version
        self._platform = platform
        self._level = level
        self._daterange = daterange
        
    @property
    def name(self):
        return self._name[:] # Return a copy
    
    @property
    def version(self):
        return self._version
    
    @property
    def platform(self):
        return self._platform
    
    @property
    def level(self):
        return self._level
    
    @property
    def daterange(self):
        return self._daterange
    
    def __eq__(self,other):
        return self is other or (
            self._name==other._name and 
            self._version == other._version and 
            self._platform == other._platform and
            self._level == other._level)
    
    def __str__(self):
        if self.platform is None:
            return 'Product('+self._name+","+str(self._version)+')'
        else:
            return "{}.Product({}, version={}, level={})".format(
                self.platform, self.name, self.version, self.level)
    
    def __repr__(self):
        return str(self)
        
    def __ne__(self,other):
        return not self==other
    
    def __hash__(self):
        return hash((self._name, self._version, self._platform, self._level, ))