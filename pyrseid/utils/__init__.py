"""
Miscellaneous utility functions.
"""
import os
import pickle
import datetime


#=============================================================#
#                      MISCELLANEOUS                          #
#=============================================================#

def is_sequence(x):
    """Is input a sequence or not?"""
    return hasattr(x,'__iter__')


def _bbox_contains(arr,val):
    return (min(arr[0:2])<=val[0] and max(arr[0:2])>=val[0] and
            min(arr[2:4])<=val[1] and max(arr[2:4])>=val[1])


#=============================================================#
#                       DIRECTORIES                           #
#=============================================================#

def path_is_local(path):
    return not path.startswith(('ftp','http'))


def ensure_dir_exists(path):
    """Create a directory if it does not already exist."""
    if not os.path.isdir(path):
        os.makedirs(path)


def printdir():
    print('Current directory (calling utils.py) is '+__file__)


def list_files(directory, recursive=False):
    """List all files in a directory, with an option for recursion.
    
    Arguments
    ---------
    directory : str
        Root directory to search for files in
    recursive : [False] | True | positive int
        Whether or not to search recursively for files.
        
        Alternatively, you can set the recursive depth by supplying a
        positive integer. Supplying a negative integer is identical to
        setting recursive to True. Supplying 0 is identical to setting
        recursive to False. 1 means look in directory and subfolders.
        2 means look in directory, subfolders, and sub-subfolders, etc.
    
    Returns
    -------
    A list of absolute file paths to all of the files found.
    
    Notes
    -----
    This function makes recursive function calls.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError('Base directory does not exist: {}'.format(
            directory))
    directory = os.path.abspath(directory)
    all_files = []
    if not (recursive in {True, False} or type(recursive) is int):
        print(recursive, type(recursive))
        raise TypeError('Recursive must be a bool {True, False} or an int.')
    if recursive is True:
        recursive = -1
    for i in os.listdir(directory):
        full_name = os.path.join(directory, i)
        if os.path.isdir(full_name):
            if recursive:
                all_files.extend(list_files(full_name, recursive=recursive-1))
        elif os.path.isfile(full_name):
            all_files.append(full_name)
    return all_files


#=============================================================#
#                         PICKLING                            #
#=============================================================#

def writevar(fname,var):
    """Write a variable into a .pkl file."""
    f = open(fname,'wb')
    pickle.dump(var,f)
    f.close()


def loadvar(path):
    """Load a variable from a .pkl."""
    assert(os.path.isfile(path))
    fobj = open(path,'rb')
    retobj = pickle.load(fobj)
    fobj.close()
    return retobj


def int_after_substr(s,substr):
    """Find instances of an integer in a string after a certain substring pattern."""
    sp = s.split(substr)
    if len(sp) is not 2:
        raise Exception('Input string contains more than one instance of substr.')
    
    after_sub = sp[1]
    isearch = 0;
    dig = None
    
    for i in range(1,len(after_sub)):
        if after_sub[:i].isdigit():
            dig = int(after_sub[:i])
        else:
            break
    return dig


#=============================================================#
#                          PRINTING                           #
#=============================================================#

def pretty_lat_print(lat):
    """Format a latitude into a string."""
    if lat < 0:
        return str(abs(lat))+'°S'
    elif lat > 0:
        return str(lat)+'°N'
    else:
        return '0°'


def pretty_lon_print(lon):
    """Format a longitude into a string."""
    if lon < 0:
        return str(abs(lon))+'°W'
    elif lon > 0:
        return str(lon)+'°E'
    else:
        return '0°'


#=============================================================#
#                            DATES                            #
#=============================================================#

def psv_date(s):
    """Returns True if input is a period-separated date string.
    Returns None if s is not a date string.
    """
    import datetime
    try:
        assert len(s) is 10
        y, m, d = s.split('.')
        return datetime.datetime(int(y), int(m), int(d))
    except:
        return None

def date_to_psv(d):
    return '.'.join([str(d.year).zfill(4),
                     str(d.month).zfill(2),
                     str(d.day).zfill(2)])

def date_to_doy(d):
    """Convert a datetime.date[time] to integer day of year (Jan. 1st = 1)"""
    return (d - type(d)(d.year,1,1)).days + 1


def doy_to_datetime(year, doy):
    """Convert the doy of a given year to a date."""
    return datetime.datetime(year, 1, 1) + datetime.timedelta(doy - 1)


#=============================================================#
#                       HTML PARSING                          #
#=============================================================#

def list_links(url, subdir=False):
    """List all links in a url. 
    
    If subdir is True, then only links ending in '/' will
    be returned.
    """
    import urllib.request, bs4
    
    try:
        site = urllib.request.urlopen(url)
    except:
        raise RuntimeError("URL: {} does not exist".format(url))
    
    html = site.read().decode('utf-8')
    soup = bs4.BeautifulSoup(html, parse_only=bs4.SoupStrainer('a', href=True))
    links = [l['href'] for l in soup.find_all('a', href=True)]
    if subdir:
        links = [l for l in links if l.endswith('/')]
    return links
