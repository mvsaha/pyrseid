from .file import File
from ...utils import list_links, psv_date, date_to_psv


_lpdaac_url_ = "http://e4ftl01.cr.usgs.gov"
def get_product_url(prod):
    return '/'.join([_lpdaac_url_, prod.satellite,
                     '.'.join([prod.name, prod.version])])


def available_dates(prod, dates=None):
    """Find the available MODIS file dates and their urls.
    
    Arguments:
        produc - modis.Product
        
        dates - [None] | sequence(datetime.datetime) | Range(datetime.datetime)
            Dates to match. If this argument is not None (the default), then
            only dates ```d``` for which ```d in dates is True``` will be
            returned
    
    Returns:
        avail_dates - dict(date:url)
            A dict in which the keys are datetime.datetimes of available 
            dates and the values are the relative path to that date folder
            on the lpdaac server.
    """
    prod_url = get_product_url(prod)
    poss_date_links = [l.strip('/\\') for l in  list_links(prod_url, subdir=True)]
    link_dates = {psv_date(l):'/'.join([prod_url, l]) for l in poss_date_links}
    if None in link_dates:
        link_dates.pop(None)
    
    if dates is not None:
        link_dates = {d:l for d, l in link_dates.items() if d in dates}
    
    return link_dates


def get_date_url(prod, date):
    """Get the LP DAAC url for a product and date."""
    return '/'.join([get_product_url(prod), date_to_psv(date)])


def available_files(prod, dates=None, tiles=None, exact_dates=False):
    
    if exact_dates: # Do we KNOW that these dates exist (i.e. not a range)
        ad = {d:get_date_url(prod, d) for d in dates}
    else:
        ad = available_dates(prod, dates=dates)
    
    af = []
    for d in sorted(ad):
        #print("Searching for files on", d, end="\r")
        print(ad[d])
        all_filenames = [l for l in list_links(ad[d]) if l.endswith('.hdf')]
        files = [File.from_path('/'.join([ad[d], f]))
            for f in all_filenames]
        if dates is not None:
            files = [f for f in files if f.date in dates]
        if tiles is not None:
            files = [f for f in files if f.tile in tiles]
        af.extend(files)
    return af

