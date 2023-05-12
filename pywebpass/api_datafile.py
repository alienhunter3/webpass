import os

from flask import Blueprint, g, current_app, request, make_response, send_file
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError
from pathlib import Path
from os.path import dirname, join, isdir, splitext, exists
from shutil import copyfile
import datetime

api_datafile = Blueprint('api_datafile', __name__)
api_prefix = '/file'


@api_datafile.before_request
def before_request_func():
    if 'password' in request.form:
        pw = request.form['password']
        try:
            g.db = PyKeePass(current_app.config['DATABASE'], password=pw)
            g.pw = pw
        except CredentialsError as e:
            return make_response({'msg': 'login invalid'}, 401)
        except Exception as e:
            current_app.logger.error(f"Unexpected error:\n{format_exc()}")
            return make_response({'msg': 'unexpected server error'}, 500)
    elif request.authorization is None:
        return make_response({'msg': 'login with http basic auth'}, 401)
    else:
        pw = request.authorization.password
        try:
            g.db = PyKeePass(current_app.config['DATABASE'], password=pw)
            g.pw = pw
        except CredentialsError as e:
            return make_response({'msg': 'login invalid'}, 401)
        except Exception as e:
            current_app.logger.error(f"Unexpected error:\n{format_exc()}")
            return make_response({'msg': 'unexpected server error'}, 500)


@api_datafile.route(api_prefix, methods=['GET'])
def get_file():
    return send_file(g.db.filename)


@api_datafile.route(api_prefix, methods=['POST'])
def update_file():
    base_dir = dirname(g.db.filename)
    archive_dir = join(base_dir, "db_archive")
    tmp_db = join(base_dir, 'tmp_db.kdbx')
    current_date = datetime.datetime.now()
    arch_fn = join(archive_dir, 'passwords-'+current_date.strftime('%Y%m%d%H%M%s')+'.kdbx')
    if exists(tmp_db):
        os.remove(tmp_db)
    if not isdir(archive_dir):
        os.mkdir(archive_dir)
    if 'db_upload' not in request.files:
        return make_response({'msg': 'bad upload'}, '400')
    file = request.files['db_upload']
    if file.filename == '':
        return make_response({'msg': 'empty file uploaded'}, '400')
    filename = file.filename
    extension = splitext(filename)[1].strip().lower()
    if extension != '.kdbx':
        return make_response({'msg': 'Wrong file type uploaded'}, '400')
    file.save(tmp_db)
    try:
        tdb = PyKeePass(tmp_db, password=g.pw)
        group_tmp = tdb.groups
    except CredentialsError as e:
        return make_response({'msg': 'DB has wrong password'}, '400')
    except AttributeError as e:
        make_response({'msg': 'Invalid db format.'}, '400')

    try:
        copyfile(g.db.filename, arch_fn)
    except:
        os.remove(tmp_db)
        return make_response({'msg': 'Error copying database to archive'}, '500')

    try:
        os.rename(g.db.filename, g.db.filename+'.bak')
    except:
        return make_response({'msg': 'Error renaming db file'}, '500')

    try:
        os.rename(tmp_db, g.db.filename)
    except:
        os.rename(g.db.filename+'.bak', g.db.filename)
        return make_response({'msg': 'Error renaming db file'}, '500')

    try:
        os.remove(g.db.filename+'.bak')
    except:
        current_app.logger.warning('Could not clean up tmpfile')

    return make_response({'msg': 'DB updated.'}, 200)


@api_datafile.route(api_prefix + "/details", methods=['GET'])
def get_file_details():
    mod_date = datetime.datetime.fromtimestamp(Path(g.db.filename).stat().st_mtime)
    size = Path(g.db.filename).stat().st_size
    num_entries = len(g.db.entries)
    num_groups = len(g.db.groups)
    payload = {"last_modified": mod_date.isoformat(), "size_bytes": size, "entries": num_entries, "groups": num_groups}
    return make_response({'msg': 'ok', 'details': payload}, 200)
