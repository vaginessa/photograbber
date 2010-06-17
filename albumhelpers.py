# albumhelpers.py
#
# A series of funcitons to build the albums datastructure

import sys, json, logging, time, os, urllib2

CAPTION = -1
DESCRIPTION = -2
LOCATION = -3

# Friends

def get_friends(q_wrap, uid):
    '''returns a list of uids and names of uid's friends'''
    
    q = ''.join(['SELECT uid, name FROM user WHERE uid IN ',
                 '(SELECT uid2 FROM friend WHERE uid1 = %(name)s) ',
                 'OR uid=%(name)s']) % {"name":uid}
    people = q_wrap(q)
    people.sort()
        
    me = dict(uid=uid,name="Myself")
    people.insert(0,me)
    return people

def get_friend(q_wrap, uid):
    '''get the name of a specific uid'''
    q = 'SELECT name FROM profile WHERE id=%s'
    res = q_wrap(q % uid)
    if res:
        return res[0]['name']
    else:
        return 'uid_%s' % uid # could not find real name

def get_friend_name(q_wrap, friends, uid):
    '''returns a person's name.  Adds the name if it doesn't exist.'''
    if uid == None:
        # this should never happen... but it did once
        return 'Unknown'
    if uid not in friends:
        friends[uid] = get_friend(q_wrap, uid)
    return friends[uid]

# Albums/Pictures

def get_tagged_albums(q_wrap, uid, albums):
    '''return info from all albums in which the uid was tagged'''
    
    q = ''.join(['SELECT aid, owner, name, modified, description, ',
                 'location, object_id FROM album WHERE aid IN (SELECT ',
                 'aid FROM photo WHERE pid IN (SELECT pid FROM photo_tag ',
                 'WHERE subject="%s"))']) % uid
    
    for item in q_wrap(q):
        item['photos'] = {}
        albums[item['aid']] = item

def get_uploaded_albums(q_wrap, uid, albums):
    '''return info from all albums uploaded by uid'''
    q = ''.join(['SELECT aid, owner, name, modified, description, ',
                 'location, object_id FROM album WHERE ',
                 'owner="%s"']) % uid

    for item in q_wrap(q):
        item['photos'] = {}
        albums[item['aid']] = item

def get_tagged_pictures(q_wrap, uid, albums):
    '''add all pictures where the user is tagged'''
    q = ''.join(['SELECT pid, aid, src_big, caption, created, object_id ',
                 'FROM photo WHERE pid IN (SELECT pid FROM photo_tag ',
                 'WHERE subject="%s")']) % uid

    for photo in q_wrap(q):
        albums[photo['aid']]['photos'][photo['pid']] = photo


def get_tagged_album_pictures(q_wrap, uid, albums):
    '''add full albums where the user is tagged'''
    q = ''.join(['SELECT pid, aid, src_big, caption, created, ',
                 'object_id FROM photo WHERE aid IN (SELECT aid ',
                 'FROM photo WHERE pid IN (SELECT pid FROM photo_tag ',
                 'WHERE subject="%s"))']) % uid

    for photo in q_wrap(q):
        albums[photo['aid']]['photos'][photo['pid']] = photo


def get_user_album_pictures(q_wrap, uid, albums):
    '''all pictures in albums uploaded by the user'''
    q = ''.join(['SELECT pid, aid, src_big, caption, created, ',
                 'object_id FROM photo WHERE aid IN (SELECT aid FROM ',
                 'album WHERE owner="%s")']) % uid
    
    for photo in q_wrap(q):
        albums[photo['aid']]['photos'][photo['pid']] = photo


def get_album_comments(q_wrap, album, friends):
    '''get the comments for a single album (including the pictures)'''
    
    q = ''.join(['SELECT object_id, fromid, time, text FROM comment ',
                 'WHERE object_id in (%s)'])

    o2pid = {} # translate object_id to pid
    oids = [] # hold object_ids to lookup

    album_comments = []

    # add each photo's caption to it's comments
    for photo in album['photos'].values():
        o2pid[photo['object_id']] = photo['pid']
        oids.append('"%s"' % photo['object_id'])
        if photo['caption']:
            photo['comments'] = [{'fromid':CAPTION,
                                  'text':photo['caption'], 'time':0}]

    oids.append('"%s"' % album['object_id'])

    # add album info to it's comments
    if album['description']:
        album_comments.append({'fromid':DESCRIPTION, 'time':0,
                               'text':album['description']})
    if album['location']:
        album_comments.append({'fromid':LOCATION, 'time':1,
                               'text':album['location']})
    
    # load all comments for album and its photos
    for item in q_wrap(q % ','.join(oids)):
        oid = item['object_id']
        if oid in o2pid: # photo comment
            clist = album['photos'][o2pid[oid]].setdefault('comments',
                                                           [])
            # add the friend's name
            item['fromname'] = get_friend_name(q_wrap, friends, item['fromid'])
            
            clist.append(item)
        else: # album comment
            album_comments.append(item)

    album['comments'] = album_comments
    
    # load tags in each photo
    q = ''.join(['SELECT pid, text, xcoord, ycoord FROM ',
                 'photo_tag WHERE pid IN(%s)'])
    pids = ['"%s"' % x for x in album['photos'].keys()]
    for item in q_wrap(q % ','.join(pids)):
        tag_list = album['photos'][item['pid']].setdefault('tags', [])
        tag_list.append(item)

def add_photo_paths(album):
    '''set path info in album dictionary'''
    for photo in album['photos'].items():
        photo[1]['path'] = os.path.join(album['folder'], '%s.jpg' % photo[0])

# Save commands

def save_albums_dict(albums, friends, path):
    '''save the albums and friends dictonaries to json files'''
    try:
        timestamp = time.strftime( "%y-%m-%d_%H-%M-%S")
        filename = os.path.join(path, 'pg_albums_%s.js' % timestamp)
        db_file=open(filename,"w")
        json.dump(albums, db_file)
        db_file.close()
        filename = os.path.join(path, 'pg_friends_%s.js' % timestamp)
        db_file=open(filename,"w")
        json.dump(friends, db_file)
        db_file.close()
    except Exception, e:
        logging.exception('Saving JSON dictionaries did not work')

def download_pic(photo, filename):
    '''downloads a picture (retries 10 times before failure)'''
    max_retries = 10
    retries = 0
    
    picout = open(filename, 'wb')
    handler = urllib2.Request(photo['src_big'])
    retry = True
    
    while retry:
        try:
            logging.debug('downloading:%s' % photo['src_big'])
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
                logging.exception('Could not download %s' % filename)
                picout.close()
                os.remove(filename)
                return

    picout.write(data.read())
    picout.close()
    os.utime(filename, (int(photo['created']),) * 2)

