import os

from .utils import is_sequence as is_sequence
from .download import grab


description = """
Attributes:
    is_local
    is_valid: Does the File represent a sufficiently 
    platform
    path
    filename
    tile
    date
    product

Comparison methods:
    __eq__() (a.k.a. ==): True for two valid files that represent the same data
    
    match(): Less stringent comparison that allows comparison with Files that are
        invalid and have wildcard values (i.e. None) for some fields.
        
InheritingClass must define:
    
    fields - tuple containing the fields that specify the File
        Maybe include some or all of the Attributes, as well as custom fields
        defined in the inheriting class. Must be members of instance.__dict__.
    
    determine_file(d) - A static method of InheritingClass that takes a dict
        that maps field_names into the actual values for that field. It returns
        a path to a remote file.
"""

def match(x,y):
    """Match two items. True if items are equal or either is None."""
    return (x is None or y is None) or (x==y)
    

"""Base class for platform-specific File objects."""
class BaseFile:
    
    """Attributes that will not change over the life of a BaseFile"""
    #_is_spec = False # Is File is fully specified (all fields are not None)?
    _is_deterministic = False # *CAN* the filename/path be determined *ONLY* from fields?
    _platform = None # str
    
    """Attributes that may change if not is_deterministic."""
    _is_determined = False # Has the filename/remotepath/path been determined?
    
    """Attributes that may change."""
    _is_local = False # Does the file exist locally?
    _is_valid = False # Do we know that this file actually exists somewhere?
    _path = None     # str
    _filename = None # str
    _shape = (0,)
    
    """Some common attributes for RS Files:"""
    _tile = None
    _date = None
    _product = None
    
    def __init__(self):
        pass
    
    def validate(self):
        raise NotImplementedError('Inheriting FileClass'
            'must implement "validate(*args)"')
    
    def determine(self):
        raise NotImplementedError('Inheriting FileClass'
            'must implement "determine_file()"')
    
    @property
    def is_local(self):
        """Is this File stored locally?"""
        return not self.path.startswith(('http://', 'ftp://'))
    
    
    @property
    def is_remote(self):
        return not self.is_local
    
    
    @property
    def is_valid(self):
        """Does a File with the specified fields exist?
        
        Returns:
            bool : This will return False for files that do not exist or that are not
                fully specified (i.e. this File was instantiated with some of the fields
                as None). Returns True if we are SURE that this File exists online
                (and we have checked).
        """
        return self._is_valid and self.is_spec
    
    
    @property
    def is_spec(self):
        """Are all of the fields fully specified?"""
        return all([getattr(self,f) is not None for f in self._fields])
    
    
    @property
    def is_determined(self):
        """Has the filename been determined."""
        return self._path is not None
    
    
    @property
    def is_deterministic(self):
        """Can a valid filename be determined with only the fields specified?
        Returns False if we need to check online to determine a filename.
        """
        return self._is_deterministic
    
    
    @property
    def platform(self):
        """What platform generated this File?"""
        return self.product.platform
    
    
    @property
    def path(self):
        """The full path to this File.
        Returns None if it is not a valid file or has not been computed."""
        if not self.is_spec:
            raise ValueError('Underspecified file has no path.')
        if self._path is None:
            self._path = self.determine(*[getattr(self,f) for f in self._fields])
        return self._path[:]
    
    
    @property
    def filename(self):
        """Return the filename.
        Returns None if it is not a valid file or has not been determined."""
        if self.is_local:
            return self.path.split(os.sep)[-1]
        else:
            return self.path.split('/')[-1]
    
    
    @property
    def extension(self):
        """Return the file extension."""
        return self.path.split('.')[-1].lower()
    
    
    @property
    def date(self):
        """Date of data collection."""
        return self._date
    
    
    @property
    def product(self):
        """What this file is measuring."""
        return self._product
    
    
    @property
    def tile(self):
        """The granule or spatial subset in this File."""
        return self._tile
    
    
    @property
    def shape(self):
        """Shape of the data contained in the file.
        By convention, the first two indices are spatial.
        """
        return self._shape
    
    
    @property
    def folder(self):
        """Return the filename."""
        if self._path is not None:
            return os.path.split(self._path)[0]
    
    
    @property
    def fields(self):
        """What elements are needed to fully specify a file."""
        return [f[:] for f in self._fields]
    
    
    def grab(self, top_dir=None, exact_dir=None, replace=False,
             update_path=True, err_action='raise', verbose=True):
        """Retrieve a file from a remote location.
        
        Arguments
        ---------
        top_dir : [None] | str
            Specify the top-level directory to place a File in. This
            will call to local_dir on the object and place it in the
            appropriate subdirectory. Either this or exact_dir should
            be given, but not both.
        exact_dir : [None] | str
            The exact directory to place the file in. No attempt will
            be made to organize it into a sub-directory based on its
            attributes.
        replace : [False] | True
            If this file already exists in the directory, should we
            replace it, downloading a new copy and overwriting the old
            file?
        update_path : [True] | False
            Should this File's path property be updated to point to the
            local file that was retrieved?
        err_action : ['raise'] | 'ignore'
            What to do if the url is invalid or cannot be downloaded:
                'raise' will raise a BadRequestError
                'ignore' will return without downloading anything.
        
        Notes
        -----
        By default, this File will be changed after the download so that
        the path that it refers to the downloaded file, not the remote one.
        
        If this file is not remote, but instead local, then nothing is done.
        
        If the download is interrupted then the partially downloaded file
        will be removed, but any folders created by this function will not
        be.
        """
        s = sum((top_dir is not None, exact_dir is not None))
        if s == 2:
            raise ValueError('Both top_dir and exact_dir were given. Only'
              ' one is allowed.')
        elif s == 0:
            raise ValueError('Must specify either top_dir or exact_dir.')
        
        if top_dir is not None:
            try:
                directory = self.local_dir(top_dir)
            except AttributeError:
                raise TypeError('Files of type <{}> have no .local_dir() method'
                  '; you must supply exact_dir instead of top_dir.'.format(
                  type(self)))
        else:
            directory = exact_dir
        
        if not os.path.isdir(directory):
            os.makedirs(directory)
        
        local_path = os.path.join(directory, self.filename)
        if replace is False and os.path.exists(local_path):
            self._path = local_path
            self._is_local = True
            return
        
        if self.is_remote and self.is_spec :
            if verbose:
                print('Downloading {}'.format(self), end=' ')
            success = grab(self.path, local_path, err_action=err_action)
            if verbose:
                print('SUCCESS' if success else 'FAILURE')
            if success:
                self._path, self._is_local = local_path, True
    
    
    def match(self, other, how=any):
        """Determine if this File matches a File or any of a sequence of Files."""
        if not is_sequence(other):
            return self._match(other)
        else:
            return how([self._match(o) for o in other])
    
    
    def _match(self,other):
        """Match a single instance."""
        return type(other) is type(self) and all(
            match(getattr(self,f),getattr(other,f)) for f in self._fields)
    
    
    def __eq__(self,other):
        eq = type(self) is type(other) and all(
            [getattr(self,f)==getattr(other,f) for f in self._fields])
        
        if eq:  # Internals to a local file if possible
            if self.is_local and not other.is_local:
                other.__dict__ = self.__dict__
            elif other.is_local and not self.is_local:
                self.__dict__ = other.__dict__
        return eq
    
    
    def __ne__(self,other):
        """Rely on user to define __eq__ for inheriting classes."""
        return not self==other
    
    
    def __hash__(self):
        return hash((self._tile,self._date,self._product))
    
    
    def __repr__(self):
        fspace = ', '.join(['{}'] * len(self._fields))
        return 'File({})'.format(fspace).format(
            *[getattr(self,f) for f in self._fields])