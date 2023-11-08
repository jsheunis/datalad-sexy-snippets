"""Create an RO-crate record from a datalad dataset"""
import argparse
import json
import mimetypes
import os
from pathlib import Path
from datalad.api import (
    status,
)

# VARIABLES
BASE_PATH = Path(os.path.realpath(__file__)).parent
META_PATH = BASE_PATH / 'ro_crate_base.json'
EXCLUDE_STRINGS = [
    '.gitattributes',
    '.gitmodules',
    '.datalad',
    '.DS_Store',
]


# FUNCTIONS

def process_status_file(item, graph_list, haspart_list):
    """"""
    # datalad.api.status() returns a generator with items
    # items could be files or datasets
    # if item is a file, it could be:
    # - .gitattributes
    # - .gitmodules
    # - .datalad/config
    # - .datalad/.gitattributes
    # - .datalad/environments/<some-env-name>/image
    # TODO: decide how to map each of these onto RO-crate entities, if at all

    # get relative path, parts, and filename
    refds = Path(item.get("refds"))
    file = Path(item.get("path"))
    relpath = file.relative_to(refds)
    print(relpath)
    if any(excl_str in str(relpath) for excl_str in EXCLUDE_STRINGS):
        return
    parts = relpath.parts
    if len(parts) == 1:
        # a file in te root directory
        add_file(str(relpath), graph_list, haspart_list)
        return
    
    for i, p in enumerate(parts):
        if i==0:
            current_relpath = p
        else:
            current_relpath = current_relpath + '/' + p
        
        if ( i + 1 ) != len(parts):
            # a directory
            if get_item_in_list("@id", current_relpath + '/', haspart_list) is None:
                add_directory(str(current_relpath), graph_list, haspart_list)
        else:
            # a file in a subdirectory
            if get_item_in_list("@id", current_relpath, haspart_list) is None:
                add_file(str(relpath), graph_list, haspart_list,
                        contentSize=item.get("bytesize"),
                        encodingFormat=mimetypes.guess_type(str(relpath))[0])


def add_file(id: str, graph_list: list, haspart_list: list,
             name=None, encodingFormat=None,
             contentSize=None, contentUrl=None):
    """"""
    haspart_record = {"@id": id}
    record = {
        "@id": id,
        "@type": "File",
        "name": name,
        "encodingFormat": encodingFormat,
        "contentSize": contentSize,
        "contentUrl": contentUrl,
    }
    record = {k: v for k, v in record.items() if v is not None}
    haspart_list.append(haspart_record)
    graph_list.append(record)
    return
    

def add_directory(id: str, graph_list: list, haspart_list: list,):
    """"""
    # directory needs to end with forward slash
    if not id.endswith('/'):
        id = id + '/'
    haspart_record = {"@id": id}
    record = {
        "@id": id,
        "@type": "Dataset",
    }
    haspart_list.append(haspart_record)
    graph_list.append(record)
    return


def get_item_in_list(key, val, test_list):
    return next(((idx, el) for idx, el in enumerate(test_list) if el[key] == val), None)


# SCRIPT

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("-a", "--annex", default='all', type=str)
args = parser.parse_args()

# Get information on all items in the dataset's filetree
res = status(
    dataset=args.dataset,
    annex=args.annex,
    result_renderer="disabled",
    return_type="generator",
)

# Initialise metadata record
with open(META_PATH) as f:
    rocrate_meta = json.load(f)
# TODO, need to initialise with required properties:
# - identifier
# - datePublished (datetime.now?)
# - name
# - description
# - license (id linking to contextual entity in the graph)

# Access main lists to be updated
graph_list = rocrate_meta["@graph"]
dataset_idx, dataset_item = get_item_in_list("@id", "./", rocrate_meta["@graph"])
haspart_list = dataset_item["hasPart"]

# Process all nodes in the filetree
for item in res:
    if item.get("status") == "ok":
        if item.get("type") == "file":
            process_status_file(item, graph_list, haspart_list)

print(rocrate_meta)