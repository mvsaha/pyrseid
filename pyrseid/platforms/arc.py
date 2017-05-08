# arc2 Functionalilty
# Contains a File class and read functions for
# African Rainfall Climatology geoTiffs, which can
# be accessed via FTP:
# <http://iridl.ldeo.columbia.edu/SOURCES/.NOAA/.NCEP/
#   .CPC/.FEWS/.Africa/.DAILY/.ARC2/.daily/>
# see "Data Source" on this above website.

from datetime import datetime
import zipfile
import numpy as np


def shape():
    return (801,751)


def isARCDateString(ds):
    try:
        y = int(ds[:4])
        m = int(ds[4:6])
        d = int(ds[6:])
        return datetime(y,m,d)
    except:
        return False


def isFile(fpath):
    '''
    s is the absolute path to the ARC2 African Rainfall Climatology geoTiff
    Returns False if the string is not a valid path or file
    Returns an ARC File object if the path is valid
    '''
    p,s = os.path.split(fpath)

    sp = s.split('.')
    if sp[0] != "africa_arc":
        return False

    d = isARCDateString(sp[1])
    if d is False:
        return False

    if sp[2] != "tif":
        return False

    if len(sp) is 4:
        if sp[-1] != "zip":
            return False

    return File(filename=s,date=d,localpath=p)


class File:
    # Modis File object
    def __init__ (self,filename,date,localpath):
        self._filename = filename

        if not isinstance(date,datetime):
            raise TypeError('Invalid Constructor: date is not a datetime object')

        if not os.path.exists(localpath):
            raise ValueError('Path to the file does not exist: '+localpath)

        joined = os.path.join(localpath,filename)
        if not os.path.exists(joined):
            raise ValueError("File does not exist locally at path: "+joined)

        self._date = date
        self._localpath = localpath

        if filename.split('.')[-1] == "zip":
            self._is_zipped = True
        else:
            self._is_zipped = False

    def __str__(self):
        return "File(ARCv2"+","+self._date.__repr__()+")"

    def __repr__(self):
        return self.__str__()

    def __eq__(self,other):

        if isinstance(other,self.__class__):
            return self._prod==other._prod and self._date==other._date

        else:
            raise Exception('Cannot compare type('+type(other)+') with'+self.__class__)

    def __ne__(self,other):
        return not self.__eq__(other)

    def folder(self):
        if self._localpath:
            return self._localpath
        else:
            return None

    def filename(self):
        return self._filename

    def fullpath(self):
        return os.path.join(self._localpath,self._filename)

    def localpath(self):
        return self._localpath

    def date(self):
        return self._date

    def __hash__(self):
        return hash(self._filename)

    def is_zipped(self):
        return self._is_zipped


def filesInFolder(folder):
    allf=[isFile(os.path.join(folder,f)) for f in os.listdir(folder)]
    return [f for f in allf if f]


def unzip(f):
    z = zipfile.ZipFile(f.fullpath())
    
    if len(z.namelist()) is not 1:
        z.close()
        raise ValueError("Expected that ARC2 zipfile contained 1 item.")
    else:
        localpath,fname = f.localpath(),z.namelist()[0]

    if os.path.exists(os.path.join(localpath,fname)):
        return isFile(os.path.join(localpath,fname)) # Will be a File
    else:
        try:
            z.extract(fname,localpath)
            z.close()
        except:
            z.close()
            return RuntimeError("Could not extract zipped ARC file:",f)

        return File(filename=fname,date=f.date(),localpath=localpath)


def read(f, missing=np.nan):
    """Read an African Rainfall Climatology File.
    The file can be in zipped or unzipped form.
    Input is an ARC File object. Output is a numpy array of data.
    """
    import gdal
    if f.is_zipped():
        f = unzip(f) # Unzip and return a File

    geotiff = gdal.Open(f.fullpath())
    if geotiff is None:
        raise RuntimeError("Could not open unzipped geotiff file",f)

    band = geotiff.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, geotiff.RasterXSize, geotiff.RasterYSize)

    del(geotiff)
    os.remove(f.fullpath())

    data[data<0] = missing

    return data


def grid():
    res = 0.1
    lo = np.arange(-20,55+res,res)
    la = np.arange(40,-40-res,-res)
    ret = {}
    ret['lat'],ret['lon'] = np.meshgrid(la,lo,indexing='ij')
    return ret
