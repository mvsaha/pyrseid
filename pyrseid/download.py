"""
Methods for downloading via http and ftp.
"""
import os

ssl_verify = False
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


#===================#
#   FTP Retreival   #
#===================#

ftp_prefix = "ftp://"
_ftp_connections_ = dict()  # Manages FTP connections based on ftp server name

def is_ftp_path(path):
    """Determine if a path is on an ftp server."""
    return path.startswith(ftp_prefix)


def parse_ftp_server(path):
    """Cut up the path to a file on an ftp server."""
    spl = path[len(ftp_prefix):].split('/')  # (server, relative_path)
    return spl[0], '/'.join(spl[1:])


def ftp_connection_active(ftp_connection):
    """Check if an ftplib.FTP object connection is active."""
    try:
        ftp_connection.voidcmd("NOOP")
        return True
    except:
        return False


def ftp_login(server, *args, **kwargs):
    """Login to an ftp server, closing an 'old' connection if it exists.
    cred is a dictionary which may contain the fields: 'user', 'pass' and 'acct'
    """
    import ftplib
    if server in _ftp_connections_:
        if not ftp_connection_active(_ftp_connections_[server]):
            _ftp_connections_[server].close()
        else:
            return _ftp_connections_[server]
    
    _ftp_connections_[server] = ftplib.FTP(server)
    _ftp_connections_[server].login(*args, **kwargs)
    return _ftp_connections_[server]


def close_all():
    """Close all existing connections to ftp servers."""
    for server in _ftp_connections_:
        _ftp_connections_[server].close
    _ftp_connections_.clear()


def grab_ftp(remote_filepath, local_filepath):
    """Download a file over ftp. Will overwrite existing files."""
    import ftplib
    
    local_directory, local_filename = os.path.split(local_filepath)
    assert os.path.exists(local_directory)
    server, relative_remote_path = parse_ftp_server(remote_filepath)
    
    # If it's the same ftp server, try to use that connection
    if (server not in _ftp_connections_) or (not ftp_connection_active(_ftp_connections_[server])):
        print("Attempting ftp login:",server, end=' ')
        ftp_login(server)
        print("SUCCESS")
    
    try:
        with open(local_filepath, 'wb') as local_file:
            _ftp_connections_[server].retrbinary("RETR "+relative_remote_path, local_file.write)
    except ftplib.error_perm as err:
        err_code = int(str(err).split()[0])  # As an integer
        print(err_code)
        raise err
        # Do something with error code ?
    except Exception as err:
        raise err


def grab_ftp_from(ftp_obj, relative_remote_path, local_filepath):
    """Download a file from an ftp server using a relative path.
    
    Arguments:
        ftp_obj - ftplib.FTP object.
            An active connection to an ftp server. The return value
            of the function "ftp_login".
        
        relative_remote_path - str
            Relative path on the FTP server.
        
        local_filepath - str
            Local filepath to be (over)written. The containing folder
            must exist or an error will be raised.
    
    """
    import ftplib
    
    local_directory, local_filename = os.path.split(local_filepath)
    assert os.path.exists(local_directory)
    #server, relative_remote_path = parse_ftp_server(remote_filepath)
    
    # If it's the same ftp server, try to use that connection
    if not ftp_connection_active(ftp_obj):
        raise RuntimeError('ftp_obj does not have an active connection.')
    
    try:
        with open(local_filepath, 'wb') as local_file:
            ftp_obj.retrbinary("RETR "+relative_remote_path, local_file.write)
    except ftplib.error_perm as err:
        err_code = int(str(err).split()[0])  # As an integer
        print(err_code)
        raise err
        # Do something with error code ?
    except Exception as err:
        raise err
    return True


def ftp_listdir(ftp_obj, path=None, match_type="d-"):
    """List files or directories in a ftp driectory.
    Arguments:
        ftp_obj - an ftplib.FTP object.
        path - str
            Relative or absolut path on the ftp server to list
            files on.
            
        match_type - ["d-"] | "d" | "-"
            How to match entries that are found. Use "d" to only
            return directories, "-" to only return files, or "d-"
            to return everything listed in the folder (the default).
            These characters represent the first column of output
            from ```ls -l``` type commands.
    """
    if path is not None:
        pwd = ftp_obj.pwd()
        ftp_obj.cwd(path)
    
    data = []
    ftp_obj.dir(data.append)
    
    if path is not None:
        ftp_obj.cwd(pwd)
    
    return [s.split(" ")[-1] for s in data if s[0] in match_type]


def ftp_listfiles(ftp_obj, path=None):
    """List files or directories in a ftp driectory.
    Arguments:
        ftp_obj - an ftplib.FTP object.
        path - str
            Relative or absolut path on the ftp server to list
            files on.
            
        match_type - ["d-"] | "d" | "-"
            How to match entries that are found. Use "d" to only
            return directories, "-" to only return files, or "d-"
            to return everything listed in the folder (the default).
            These characters represent the first column of output
            from ```ls -l``` type commands.
    """
    if path is not None:
        return ftp_obj.nlst(path)
    else:
        return ftp_obj.nlst()


#====================#
#   HTTP Retreival   #
#====================#

http_prefix = "http://"
https_prefix = "https://"
def is_http_path(path):
    return path.startswith(http_prefix) or path.startswith(https_prefix)


def grab_http(remote_filepath, local_filepath, chunk_size=1048567):
    """Download a file over http."""
    import requests, os
    response = requests.get(remote_filepath, stream=True)
    check_request(response)
    with open(local_filepath, 'wb') as local_file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                local_file.write(chunk)
                local_file.flush()
                os.fsync(local_file.fileno())
    return True


def grab_https(remote_filepath, local_filepath, chunk_size=1048567, ssl_verify=ssl_verify):
    """Download a file over https."""
    import requests, os
    response = requests.get(remote_filepath, stream=True, verify=ssl_verify)
    check_request(response)
    
    with open(local_filepath, 'wb') as local_file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                local_file.write(chunk)
                local_file.flush()
                os.fsync(local_file.fileno())
    return True


class BadRequestError(Exception):
    """Raised when a file is requested that does not exist."""

# Known pages that are redirects when a file is missing
_bad_request_pages = {
    
    # For TRMM files
    'http://disc.sci.gsfc.nasa.gov/404.html',
}

_exceptions_to_bad_request = {}

def check_request(response):
    """Verify that the response is the file we requested, raising a
    BadRequestError if the file does not exist.
    
    Arguments
    ---------
    response - requests.Response object
        The response from the url that we are trying to download.
    
    Notes
    -----
    This functionality is needed because requesting a File that does not 
    exist can sometimes redirect to a 404 page, which, while signaling
    an error, actually returns a status code of 200 (OK). Therefore
    we must directly check against these pages to ensure that we are
    actually.
    """
    if response.url in _bad_request_pages:
        raise BadRequestError('Could not process the request {} with code'
          '<{}>'.format(response.url, response.status_code))


#=============#
#   Wrapper   #
#=============#        

def grab(remote_filepath, local_filepath, err_action='raise', html_chunk_size=1048567):
    """Download a remote file to a local directory.
    
    Arguments
    ---------
    remote_filepath : str
        The url of the remote file (http or ftp)
    local_filepath : str
       Where to put the downloaded file.
    err_action : ['raise'] | 'ignore'
        What to do if the url is invalid or cannot be downloaded. 'raise'
        will raise a BadRequestError,  'ignore' will return without
        downloading anything.
    html_chunk_size [1048567] | int
        The chunk_size to stream an html file with in bytes. Defaults to 1 MB.
    
    Returns
    -------
    bool indicating if the download was successful (True) or failed (False)
    
    Raises
    ------
    BadRequestError if err_action is 'raise' and the url is not valid.
    """
    if not err_action in {'raise', 'ignore'}:
        raise ValueError('err_action must be "ignore" or "raise".')
    success = False
    try:
        if is_ftp_path(remote_filepath):
            success = grab_ftp(remote_filepath, local_filepath)
        elif is_http_path(remote_filepath):
            success = grab_http(remote_filepath, local_filepath, chunk_size=html_chunk_size)
        else:
            raise ValueError("Don't know how to download remote file :{}"
              "only http and ftp are supported.".format(remote_filepath))
    except BadRequestError as e:
        if err_action == 'raise':
            raise e
        else:
            return False
    except Exception as e:
        # Clean up a partially a downloaded file
        if not success and os.path.exists(local_filepath):
            os.remove(local_filepath)
        raise e
    return True


