#hook-huggingface_hub.py

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('huggingface_hub')

