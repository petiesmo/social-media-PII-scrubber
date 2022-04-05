#hook-en_core_web_sm.py

from gc import collect
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('en_core_web_sm')
hidden_imports = collect_submodules('en_core_web_sm')