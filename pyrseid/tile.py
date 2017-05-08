"""
Classes representing tiles/granules and swaths of tiles.
"""

import sys
sys.dont_write_bytecode = True

class BaseTile:
    """Represents a Granule or Tile of data with two indices (v,h)."""
    def __init__(self,v,h):
        try: # Check horizontal component
            assert(h in self._hrange)
        except(AssertionError):
            raise ValueError("Horizontal Tile (h) component is out of range."+
                             str(self._hrange))
        except(AttributeError):
            raise ValueError("'_hrange' member must be implemented by inheriting class.")
        
        try: # Check vertical component
            assert(v in self._vrange)
        except(AssertionError):
            raise ValueError("Vertical Tile (v) component is out of range: "+
                             str(self._vrange))
        except(AttributeError):
            raise ValueError("'_vrange' member must be implemented by inheriting class.")
        
        self._v,self._h = v,h
        
    @property
    def h(self):
        """Horizontal coordinates of a Tile."""
        return self._h
    
    @property
    def v(self):
        """Vertical coordinates of a Tile"""
        return self._v
    
    def __repr__(self):
        return 'Tile(h='+str(h)+',v='+str(v)+')'
    
    def __eq__(self, other):
        return self is other or (self.h==other.h and self.v==other.v)
    
    def __ne__(self,other):
        return not self==other
    
    def __ge__(self, other):
        return (self.v, self.h) >= (other.v, other.h)
    
    def __le__(self, other):
        return not self >= other
    
    def __gt__(self, other):
        return (self.v, self.h) >= (other.v, other.h)
    
    def __lt__(self, other):
        return not self > other
    
    def __hash__(self):
        return hash((self.h,self.v))
    

class TileRange:
    """A rectangular grid of Tiles."""
    def __init__(self,tile1,tile2):
        if not isinstance(tile1,BaseTile) or not isinstance(tile2,BaseTile):
            raise TypeError("Inputs must be Tiles or inherited from Tiles.")
        
        if not type(tile1)==type(tile2):
            raise TypeError("Inputs must be the same type of tile (e.g. Modis or GFC)")
        self._type = type(tile1)
        h = (tile1.h,tile2.h)
        v = (tile1.v,tile2.v)
        self.tiles = [type(tile1)(v=min(v),h=min(h)),type(tile1)(v=max(v),h=max(h))]
        
    def __len__(self):
        return (self.tiles[1].h-self.tiles[0].h+1)*(self.tiles[1].v-self.tiles[0].v+1)
    
    def __str__(self):
        return "TileRange("+str(self.tiles[0])+" to "+str(self.tiles[1])+")"
    
    def __repr__(self):
        return self.__str__()
    
    def to_list(self):
        '''Expand TileRange into a list of Tiles'''
        return [self._type(h=h,v=v)
                    for h in range(self.tiles[0].h,self.tiles[1].h+1)
                        for v in range(self.tiles[0].v,self.tiles[1].v+1) ]
    
    def __iter__(self):
        """Return an iterator over all pixels."""
        return iter(self.to_list())

    def __contains__(self,tile):
        return (min(self.tiles[0].h,self.tiles[1].h) <= tile.h and
                max(self.tiles[0].h,self.tiles[1].h) >= tile.h and
                min(self.tiles[0].v,self.tiles[1].v) <= tile.v and
                max(self.tiles[0].v,self.tiles[1].v) >= tile.v )