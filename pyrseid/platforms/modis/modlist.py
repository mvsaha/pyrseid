def has_modlist(modfolder,prod,date):
    """Check if a modfolder/prodfolder/datefolder has a modlist.

    PARAMETERS:
        modfolder - str
            Top-level modis directory

        prod - modis.Product

        date - datetime.datetime

    RETURNS:
        True if modfolder/prodfolder/datefolder has a .modlist
        False if modlist does not exist or datefolder or prodfolder do not exist.
    """
    fullpath = os.path.join(modfolder,str(prod),date_to_psv(date))
    if os.path.exists(fullpath):
        files = os.listdir(fullpath)
        if '.modlist' in files:
            return os.path.join(fullpath,'.modlist')
        else:
            return False
    else:
        return False


def remove_modlist(toppath,prod,date):
    """Remove a .modlist from a product."""
    modlist = has_modlist(toppath,prod,date)
    if modlist:
        os.remove(modlist)


def create_modlist(modfolder,prod,date,list_of_modisFiles):
    '''Build a modlist with a list of files.
    NOTES:
        Will create the prodfolder and datefolder if they do not exist.
    '''
    datefolder = os.path.join(modfolder,str(prod),date_to_psv(date))
    if not os.path.exists(datefolder):
        os.makedirs(datefolder)

    filename = '.modlist'
    modlist_file = open(os.path.join(datefolder,filename),'w')
    for f in list_of_modisFiles: # Writes nothing if list is empty
        modlist_file.write(str(f)+'\n')
    modlist_file.close()


def read_modlist(exactpath):
    '''Read a .modlist file.'''
    if not os.path.exists(exactpath) or not exactpath.endswith('.modlist'):
        raise ValueError('A .modlist does not exist in this folder:['+
                            modfolder+','+str(prod)+','+date+']')

    fmodlist = open(exactpath,'r')
    files=[File(f.strip()) for f in fmodlist]
    fmodlist.close()
    for f in files:
        assert(f.is_valid)
    
    return files