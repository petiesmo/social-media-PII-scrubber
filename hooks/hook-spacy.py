#hook-spacy.py

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
#import spacy

datas = collect_data_files('spacy', False)
#datas.append((spacy.util.get_data_path(), 'spacy/data'))

datas.extend(collect_data_files('thinc', False))

hiddenimports=[
    'blis',
    'cymem.cymem',
    'murmurhash',
    'preshed.maps',
    'srsly.msgpack.util',
    'thinc'
    ]

hiddenimports.extend(collect_submodules('spacy'))