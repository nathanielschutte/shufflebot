
import json
from os import write

PERSIST_MANIFEST = 'manifest.json'
PERSIST_FILE_EXT = '.dat'
storageDir = './'

storage = {}
meta = {
    'count': 0,
    'list': []
}

# Storge directory
def setDir(dir):
    global storageDir
    storageDir = dir
    print(f'storage: using directory {storageDir}')

# AFTER load - add collection to storage, store in file, update meta
def useCollection(name):
    if len(storage) > 0 and name in storage:
        return
    else:
        storage[name] = {}
        meta['count'] = meta['count'] + 1
        meta['list'].append(name)
        print(f'storage: added collection [{name}]')
        persistCollection(name)
        writeManifest()


# Access a collection for reading and writing
def getCollection(name):
    return storage[name]

# Does this collection exist
def hasCollection(name):
    return name in storage

# Clear a collection
def clearCollection(name):
    if name in storage:
        storage[name] = {}

# Set entire collection
def setCollection(name, data):
    if name in storage and storage[name] != None:
        storage[name] = data

# Set a collection item (can just use getCollection reference)
def setCollectionItem(name, key, item):
    if name in storage and storage[name] != None:
        storage[name][key] = item

# Remove a collection item
def removeCollectionItem(name, key):
    if name in storage and storage[name] != None:
        if key in storage[name]:
            del storage[name][key]

# Write the manifest file
def writeManifest():
    manifest = open(storageDir + PERSIST_MANIFEST, 'w')
    manifest.write(json.dumps(meta))
    manifest.close()

# Load all state data
def load():
    global storage
    global meta

    n = 0 # loaded collections count
    newList = [] # loaded collections keys
    rewrite = False # should meta be rewritten
    manifest = None
    try:
        manifest = open(storageDir + PERSIST_MANIFEST, 'r')
        metastr = ''.join(manifest.readlines())
        if metastr == None or len(metastr) == 0 or metastr == '':
            print('storage: metadata object empty')
            return
        metaobj = json.loads(metastr)
        if metaobj != None and len(metaobj) > 0 and 'count' in metaobj and 'list' in metaobj:
            meta = metaobj
        else:
            print('storage: bad metadata object')
            return

        count = meta['count']
        list = meta['list']

        # If metadata was successfully loaded it is rewritable
        rewrite = True

        for item in list:
            try:
                file = open(storageDir + item + PERSIST_FILE_EXT, 'r')
                str = ''.join(file.readlines())
                if len(str) > 0:
                    collection = json.loads(str)
                    if collection != None:
                        storage[item] = collection
                        newList.append(item)
                        print(f'storage: loaded collection [{item}] ({len(collection)} lines)')
                        n += 1
            except:
                print(f'storage: error loading collection [{item}]')
            finally:
                file.close()
        
        print(f'storage: finished loading {n} collections (expected {count})')

    except:
        print(f'storage: error reading storage data')
    finally:
        if manifest != None:
            manifest.close()
        if rewrite:
            meta['count'] = n
            meta['list'] = newList
            writeManifest()
            print('storage: rewriting metadata')

# Store collection data
def persistCollection(name):
    if storage != None and len(storage) > 0 and name in storage:
        str = json.dumps(storage[name])

        try:
            f = open(storageDir + name + PERSIST_FILE_EXT, "w")
            f.write(str)
            print(f'storage: wrote collection [{name}] ({len(storage[name])} lines)')
        except:
            print(f'storage: error writing collection [{name}]')
        finally:
            f.close()

    else:
        print(f'storage: no collection data for [{name}]')


def persistAll():
    pass