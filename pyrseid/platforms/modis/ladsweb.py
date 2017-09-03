from .file import File
from ...download import ftp_login, ftp_listdir, ftp_listfiles
from ...utils import list_links, doy_to_datetime


_ladsweb_server_name = "ladsweb.nascom.nasa.gov"
def available_dates(product, dates=None):
    """Find available MODIS file dates and ftp paths.
    
    Arguments:
        produc - modis.Product
        
        dates - [None] | sequence(datetime.datetime) | Range(datetime.datetime)
            Dates to match. If this argument is not None (the default), then
            only dates ```d``` for which ```d in dates is True``` will be
            returned
    
    Returns:
        avail_dates - dict(date:ftp_path)
            A dict in which the keys are datetime.datetimes of available 
            dates and the values are the relative path to that date folder
            on the ladsweb ftp server.
    """
    server = ftp_login(_ladsweb_server_name)
    prod_dir = "allData/{}/{}".format(int(product.version), product.name)
    year_dirs = ftp_listdir(server, prod_dir, match_type="d")
    
    # Construct a new sequence or object type with the years that are present
    if dates is not None:
        year_dates = type(dates)([i.year if i is not None else i for i in dates])
        year_dirs = [yd for yd in year_dirs if int(yd) in year_dates]
    
    avail_dates = dict()
    
    for yd in year_dirs:
        s_doys = ftp_listdir(server, '/'.join([prod_dir, yd]), match_type="d")
        for s_doy in s_doys:
            date = doy_to_datetime(int(yd), int(s_doy))
            if dates is not None and date not in dates:
                continue
            avail_dates[date] = '/'.join([prod_dir, yd, s_doy])
    return avail_dates


def available_files(prod, dates=None, tiles=None):
    server = ftp_login(_ladsweb_server_name)
    ad = available_dates(prod, dates=dates)
    af = []
    print("Searching for available files in dates")
    
    for d in sorted(ad):
        print("Searching for files on", d, end="\r")
        #sys.stdout.flush()
        
        all_filenames = ftp_listfiles(server, ad[d])
        files = [File.from_path("ftp://" + '/'.join(
            [_ladsweb_server_name, f])) for f in all_filenames]
        if tiles is not None:
            files = [f for f in files if f.tile in tiles]
        af.extend(files)
    return af