import sys
sys.dont_write_bytecode = True

import numpy as np


class Range:
    """Class representing a numeric range."""
    
    def __init__(self, *args):
        """
        Args
        ----
        lower, upper : inclusive bounds of the Range
        
        """
        # TODO: Fix input arguments.
        if len(args) is 1:
            lower, upper = args[0]
        elif len(args) is 2:
            lower, upper = args
        else:
            raise ValueError(
                "Range must be called with a len-2 sequence of two args.")
        
        if lower is not None and upper is not None:
            self._lower,self._upper = min(lower,upper), max(lower,upper)
        else:
            self._lower, self._upper = lower,upper
            
    def __contains__(self,val):
        """ Test if a value is inside the Range. Bounds are inclusive and None
        represents and infinite bound. Therefore, Any """
        return ((self._lower is None or val >= self._lower) and
                (self._upper is None or val <= self._upper))
    
    @property
    def lower(self):
        return self._lower
    
    @property
    def upper(self):
        return self._upper
    
    def __str__(self):
        return '['+str(self.lower)+','+str(self.upper)+']'
    
    def __repr__(self):
        return 'Range('+str(self.lower)+','+str(self.upper)+')'
    
    def __getitem__(self, i):
        return (self.lower, self.upper)[i]
    
    
class BoundingBox:
    """Bounding box for geographic coordinates.
    Bounds are always inclusive."""
    
    def __init__(self, n, s, w, e, dtype=float):
        """Create a BoundingBox with bounds"""
        self._arr = np.array([n, s, w, e],dtype=dtype)
        self._dtype = dtype
        self._n, self._s, self._w, self._e = n, s, w, e
    
    @staticmethod
    def from_bool_img(boolimg):
        """Create a BoundingBox for all True pixels in a 2d bool image."""
        assert( len(boolimg.shape) is 2  and  boolimg.dtype=='bool')
        y,x = np.where(boolimg)
        return BoundingBox(y.min(), y.max(), x.min(), x.max(), dtype=int)
        
    
    @property
    def n(self):
        return self._n
    
    @property
    def s(self):
        return self._s
    
    @property
    def e(self):
        return self._e
    
    @property
    def w(self):
        return self._w
    
    @property
    def dtype(self):
        return self._dtype
    
    @property
    def shape(self):
        if self._dtype is not int:
            raise AttributeError("non-int BoundingBoxes do not have a shape.")
        
        return abs(self.n - self.s) + 1, abs(self.w - self.e) + 1
    
    
    def slice(self, ns=True, we=True, yx=True):
        """Produce a slice that can be used to index numpy arrays."""
        assert(self._dtype == int)
        
        if ns:
            ns_slice = slice(self.n, self.s + 1)
        else:
            ns_slice = slice(self.s, self.n + 1)
            
        if we:
            we_slice = slice(self.w, self.e + 1)
        else:
            we_slice = slice(self.e, self.w + 1)
        
        if yx:
            return (ns_slice, we_slice)
        else:
            return (we_slice, ns_slice)
    
    
    def __repr__(self):
        return 'BoundingBox([{}:{}], [{}:{}])'.format(
            self.s, self.n, self.w, self.e)
    
    
    def __contains__(self, yx):
        return ((self.n >= yx[0]) & (self.s <= yx[0]) &
                (self.w <= yx[1]) & (self.e >= yx[1]))
    
        
    def __call__(self, yx):
        """Test 'in'-ness of a yx"""
        return ((self.n >= yx[0]) & (self.s <= yx[0]) &
                (self.w <= yx[1]) & (self.e >= yx[1]))
