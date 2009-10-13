from distutils.core import setup
import py2exe, sys, os

sys.argv.append('py2exe')

setup(
        data_files = [("img",["img/1.ppm","img/2.ppm","img/3.ppm","img/4.ppm","img/pg.ico"])],
        options = {'py2exe': {'optimize':2}},
        windows = [{'script': 'pg.py'}],
        zipfile = None,
)
