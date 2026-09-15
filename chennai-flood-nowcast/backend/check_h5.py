import h5py
import glob, os

def find_keys(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(name)

files = glob.glob(os.path.join(os.environ.get('TEMP', 'C:\\Temp'), '*.HDF5'))
if files:
    f_path = max(files, key=os.path.getctime)
    f = h5py.File(f_path, 'r')
    f.visititems(find_keys)
    f.close()
else:
    print('No HDF5 temp file found')
