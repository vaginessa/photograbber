from distutils.core import setup
import py2exe, sys, os

sys.argv.append('py2exe')

setup(
        data_files = [("img",["img/creepon.ppm","img/download.ppm","img/login.ppm","img/quit.ppm","img/pg.ico"])],
        options = {'py2exe': {'optimize':2}},
        windows = [{'script': 'pg.py'}],
        zipfile = None,
)
