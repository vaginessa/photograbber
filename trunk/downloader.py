from facebook import Facebook
import os, urllib,urllib2
from threading import Thread

class FBDownloader(Thread):

    def __init__ (self, photos_path, facebook, update_callback, error_callback):
        Thread.__init__(self)
        self.photos_path = photos_path
        self.facebook = facebook
        self.update = update_callback
        self.error = error_callback

    def run(self):
        try:
            # photos = self.facebook.photos.get(self.facebook.uid)
            photos = self.facebook.fql.query("SELECT pid, aid, src_big FROM photo WHERE pid IN (SELECT pid FROM photo_tag WHERE subject=" + str(self.facebook.uid) + ")")

            # some helpful variables
            dirName = self.photos_path + '/'

            # used by update
            index = 0
            total = len(photos)

            # download each photo
            for photo in photos:
                pid = photo['pid']
                url = photo['src_big']

                if not os.path.isfile(dirName + pid + '.jpg'):
                    if not os.path.isdir(dirName):
                        os.mkdir(dirName)

                    picout = open(dirName + pid + '.jpg', "wb")
                    picPageFile = (urllib2.urlopen(urllib2.Request(url))).read()
                    picout.write(picPageFile)
                    picout.close()

                # update progressbar
                index = index + 1
                self.update(index, total)

        except Exception, e:
            self.error(e)
