import os, re, sys, urllib2, time
from threading import Thread
import multiprocessing
import albumhelpers
import logging

class FBDownloader(Thread):
    REPLACE_RE = re.compile(r'\*|"|\'|:|<|>|\?|\\|/|\|,| ')

    def __init__ (self, photos_path, uid, friends,
                        full_albums, user_albums, extras, facebook,
                        update_callback, force_exit_callback):
        Thread.__init__(self)
        self.photos_path = photos_path
        self.uid = uid
        self.friends = friends
        self.facebook = facebook
        # options
        self.full_albums = full_albums
        self.user_albums = user_albums
        self.extras = extras
        # callback functions
        self.update = update_callback
        self.force_exit = force_exit_callback

        self._thread_terminated = False
        self.index = self.total = 0
        self.albums = {}        # hold all pic data

    # terminate the thread if need be
    def exit_if_terminated(self):
        if self._thread_terminated:
            logging.info('GUI terminating download thread')
            if self.po:
               self.po.terminate() # stop workers
            sys.exit() # raise SystemExit exception to terminate run()

    # queries fail a lot, retry them many times
    def query_wrapper(self, q):
        max_retries = 10
        retries = 0
        while True:
            # check if thread should be terminated
            self.exit_if_terminated()
            try:
                return self.facebook.fql.query(q)
            except Exception, e:
                if retries < max_retries:
                    logging.info('retrying function: %d\n' % retries)
                    retries += 1
                    # sleep longer and longer between retries
                    time.sleep(retries * 2)
                else:
                    raise

    # return a persons name
    def friend_name(self, uid):
        if uid == None:
            # this should never happen... but it did once
            return 'Unknown'
        if uid not in self.friends:
            self.friends[uid] = albumhelpers.get_friend(self.query_wrapper, uid)
        return self.friends[uid]

    # functions to write extra info

    def write_comments(self, filename, comments):
        fp = open(filename, 'w')
        for comment in sorted(comments, key=lambda x:x['time']):
            if comment['fromid'] == albumhelpers.CAPTION:
                fp.write('Photo Caption\n')
            elif comment['fromid'] == albumhelpers.DESCRIPTION:
                fp.write('Album Description\n')
            elif comment['fromid'] == albumhelpers.LOCATION:
                fp.write('Album Location\n')
            else:
                friend = self.friend_name(comment['fromid'])
                fp.write('%s ' % time.ctime(int(comment['time'])))
                fp.write('%s\n' % friend.encode('utf-8'))
            fp.write('%s\n\n' % comment['text'].encode('utf-8'))
        fp.close()
        os.utime(filename, (int(comment['time']),) * 2)

    def write_tags(self, filename, tags, file_time):
        fp = open(filename, 'w')
        for tag in sorted(tags, key=lambda x:(float(x['xcoord']),
                                              float(x['ycoord']))):
            fp.write('%9.5f %9.5f %s\n' % (tag['xcoord'], tag['ycoord'],
                                           tag['text'].encode('utf-8')))
        fp.close()
        os.utime(filename, (file_time,) * 2)


    # get albums and photos

    def get_albums(self):
        albumhelpers.get_tagged_albums(self.query_wrapper, self.uid, self.albums)
        if self.user_albums:
            albumhelpers.get_uploaded_albums(self.query_wrapper, self.uid, self.albums)

    def get_pictures(self):
        if self.full_albums:
            albumhelpers.get_tagged_album_pictures(self.query_wrapper, self.uid, self.albums)
        else:
            albumhelpers.get_tagged_pictures(self.query_wrapper, self.uid, self.albums)

        if self.user_albums:
            albumhelpers.get_user_album_pictures(self.query_wrapper, self.uid, self.albums)

    # process an album
    def save_album(self, album):
        self.exit_if_terminated()

        if self.extras:
            albumhelpers.get_album_comments(self.query_wrapper, album)

        username = self.friend_name(album['owner'])
        album_folder = self.REPLACE_RE.sub(
                '_', '%s-%s' % (username, album['name']))
        album_path = os.path.join(self.photos_path, album_folder)

        # Create album directory if it doesn't exist
        if not os.path.isdir(album_path):
            os.mkdir(album_path)

        # Save album comments, will only exist if we fetched them
        if album['comments']:
            meta_path = os.path.join(album_path, 'ALBUM_COMMENTS.txt')
            self.write_comments(meta_path, album['comments'])

        # Concurrent download functionality
        self.po = multiprocessing.Pool(processes=5)
        
        for photo in album['photos'].items():
            # photo is a tuple, [0] pid, [1] dictionary
            self.save_photo(album_path, *photo)

        # Stop accepting more work
        self.po.close()

        # Wait for all workers to finish
        while multiprocessing.active_children():
            self.exit_if_terminated()
            time.sleep(1)            
        self.po.join()

        # Reset modify time after adding files
        # (must happen after threads finish)
        os.utime(album_path, (int(album['modified']),) * 2)

    # process a photo
    def save_photo(self, album_path, pid, photo):
        self.exit_if_terminated()

        # Save extra info
        if 'comments' in photo:
            meta_name = os.path.join(album_path, '%s_comments.txt' % pid)
            self.write_comments(meta_name, photo['comments'])

        if 'tags' in photo:
            meta_name = os.path.join(album_path, '%s_tags.txt' % pid)
            self.write_tags(meta_name, photo['tags'], int(photo['created']))

        # Get the file...
        filename = os.path.join(album_path, '%s.jpg' % pid)
        photo['path'] = filename
        
        # If file already exists don't download
        if os.path.isfile(filename):
            self.photo_saved(None) # but update counter
            return

        # Add download task to worker queue
        self.po.apply_async(download, (photo, filename,), callback = self.photo_saved)

    # called when save_photo task is **successfully** completed
    def photo_saved(self, r):
        self.index += 1
        self.update(self.index, self.total)

    # the main show
    def run(self):
        try:
            self.get_albums()
            self.get_pictures()
            self.total = sum(len(album['photos'])
                             for album in self.albums.values())

            # Create Download Directory (recursively)
            if not os.path.isdir(self.photos_path):
                os.makedirs(self.photos_path)

            # save each album
            for album in self.albums.values():
                self.save_album(album)

            # save data to file
            albumhelpers.save_albums(self.albums, self.photos_path)
        except Exception, e:
            logging.exception('problem in download thread')
            self.exit_if_terminated()
            self.force_exit() # kill GUI
            sys.exit(1) # kill thread
        self.update(self.index,self.total,done=True)

def download(photo, filename):
    max_retries = 10
    retries = 0
    
    picout = open(filename, 'wb')
    handler = urllib2.Request(photo['src_big'])
    retry = True
    
    while retry:
        try:
            data = urllib2.urlopen(handler)
            retry = False
        except Exception, e:
            if retries < max_retries:
                retries += 1
                logging.debug('retrying download %s' % filename)
                # sleep longer and longer between retries
                time.sleep(retries * 2)
            else:
                # skip on 404 error: Issue 13
                logging.warning('Could not download %s' % filename)
                picout.close()
                os.remove(filename)
                return

    picout.write(data.read())
    picout.close()
    os.utime(filename, (int(photo['created']),) * 2)
