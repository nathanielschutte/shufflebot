
import json
import os
import shutil

PERSIST_FILE_EXT = '.json'
PERSIST_MANIFEST = 'manifest.json'
PERSIST_STORE_DEFAULT = './storage'

class Storage:
    """Very simple collection storage using JSON"""

    def __init__(self, dir=PERSIST_STORE_DEFAULT) -> None:
        self.dir = dir.strip()

        # store dir check
        self.__checkdir(dir)

        # collection data
        self.storage = {}
        self.meta_count = 0
        self.meta_list = []

        self.loaded = False

    # Storge directory
    def setDir(self, dir):
        self.dir = dir
        print(f'storage: using directory {self.dir}')

    # AFTER load - add collection to storage, store in file, update meta
    def useCollection(self, name):
        if len(self.storage) > 0 and name in self.storage:
            return
        else:
            self.storage[name] = {}
            self.meta_count = self.meta_count + 1
            self.meta_list.append(name)
            print(f'storage: added collection [{name}]')
            self.persistCollection(name)
            self.writeManifest()


    # Access a collection for reading and writing
    def getCollection(self, name):
        return self.storage[name]

    # Does this collection exist
    def hasCollection(self, name):
        return name in self.storage

    # Clear a collection
    def clearCollection(self, name):
        if name in self.storage:
            self.storage[name] = {}

    # Set entire collection
    def setCollection(self, name, data):
        if name in self.storage and self.storage[name] != None:
            self.storage[name] = data

    # Set a collection item (can just use getCollection reference)
    def setCollectionItem(self, name, key, item):
        if name in self.storage and self.storage[name] != None:
            self.storage[name][key] = item

    # Remove a collection item
    def removeCollectionItem(self, name, key):
        if name in self.storage and self.storage[name] != None:
            if key in self.storage[name]:
                del self.storage[name][key]

    # Write the manifest file
    def writeManifest(self):
        manifest = open(self.dir + PERSIST_MANIFEST, 'w')
        manifest.write(json.dumps(self.__getmeta()))
        manifest.close()

    # Load all state data
    def load(self):

        n = 0 # loaded collections count
        newList = [] # loaded collections keys
        rewrite = False # should meta be rewritten
        manifest = None

        try:
            manifest = open(self.dir + PERSIST_MANIFEST, 'r')
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

            # temp metadata
            count = meta['count']
            list = meta['list']

            # if metadata was successfully loaded it is rewritable
            rewrite = True

            for item in list:
                try:
                    file = open(self.dir + item + PERSIST_FILE_EXT, 'r')
                    str = ''.join(file.readlines())
                    if len(str) > 0:
                        collection = json.loads(str)
                        if collection != None:
                            self.storage[item] = collection
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
                self.meta_count = n
                self.meta_list = newList
                self.writeManifest()
                print('storage: rewriting metadata')

    # Store collection data
    def persistCollection(self, name):
        if self.storage != None and len(self.storage) > 0 and name in self.storage:
            str = json.dumps(self.storage[name])

            try:
                f = open(self.dir + name + PERSIST_FILE_EXT, "w")
                f.write(str)
                print(f'storage: wrote collection [{name}] ({len(self.storage[name])} lines)')
            except:
                print(f'storage: error writing collection [{name}]')
            finally:
                f.close()

        else:
            print(f'storage: no collection data for [{name}]')


    # ...
    def persistAll():
        pass

    # Get metadata 'object'
    def __getmeta(self):
        return {
            'count': self.meta_count,
            'list': self.meta_list
        }

    # Check storage path
    def __checkdir(self, dir):
        if (not os.path.exists(dir)):
            self.dir = PERSIST_STORE_DEFAULT
        else:
            self.dir = dir

        # add path div
        if (self.dir.strip()[-1] != '/'):
            self.dir = self.dir.strip() + '/'