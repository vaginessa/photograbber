# albumhelpers.py
#
# A series of funcitons to build the albums datastructure

import sys, json, logging, time, os

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
    '''Get the name of a specific uid'''
    q = 'SELECT name FROM profile WHERE id=%s'
    res = q_wrap(q % uid)
    if res:
        return res[0]['name']
    else:
        return 'uid_%s' % uid # could not find real name

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


def get_album_comments(q_wrap, album):
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
            #item['fromname'] = friend_name(item['fromid'])
            
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

def get_extra_info(q_wrap, albums):
    for album in albums.values():
        get_album_comments(q_wrap, album)
        for photo in album['photos'].items():
            

def save_albums(albums, path):
    '''save the album info to a json database'''
    timestamp = time.strftime( "%y-%m-%d_%H-%M-%S")
    filename = os.path.join(path, 'photograbber_%s.js' % timestamp)
    db_file=open(filename,"w")
    json.dump(albums, db_file)
    db_file.close()
