from distutils.core import setup
import py2exe, sys, os

sys.argv.append('py2exe')

setup(
        data_files = [( "dep",["dep/creepon.ppm",
                              "dep/download.ppm",
                              "dep/login.ppm",
                              "dep/quit.ppm",
                              "dep/pg.ico",
                              "dep/viewer.html",]),
                        "INSTALL.txt",
                        "LICENSE.txt"],
        options = {'py2exe': {'bundle_files':3}},
        windows = [{'script': 'pg.py', "icon_resources":[(1,"dep/pg.ico")]}],
        zipfile = None
)
