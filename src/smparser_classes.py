#smparser-class

from pathlib import Path
SUPPORTED_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']

class SMParser():
    def __init__(self, zippath):
        self.zippath = Path(zippath)
        self.json_files = []
        self.csv_files = []

    #Utility Functions
    def blur_faces(img_path):
        pass
        return None
    def genCSV():
        pass
        return None
    def unzip(platform, temp_path):
        pass
        return None
    def ask_date():
        pass
        return None
    def out_of_range():
        pass
        return None
    #Unip and locate files
    
    #Parse Functions

class FBParser(SMParser):
    def __init__(self, zippath):
        super.__init__(self,zippath)
        
    
    