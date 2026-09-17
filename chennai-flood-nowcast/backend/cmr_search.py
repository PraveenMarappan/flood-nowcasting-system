import requests
import json

# IMERG Final Run V07 for 2015-11-20 to 2015-12-05
# Usually short_name is GPM_3IMERGHDF

def search_collections():
    url = "https://cmr.earthdata.nasa.gov/search/collections.json?keyword=IMERG*Final*&page_size=10"
    r = requests.get(url)
    entries = r.json().get('feed', {}).get('entry', [])
    for e in entries:
        print(e.get('short_name'), e.get('dataset_id'))

def search_granules(short_name, start_date, end_date):
    url = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name={short_name}&temporal={start_date},{end_date}&page_size=2"
    r = requests.get(url)
    entries = r.json().get('feed', {}).get('entry', [])
    if not entries:
        print(f"No granules for {short_name}")
        return
    for e in entries:
        links = e.get('links', [])
        hdf5_link = next((l['href'] for l in links if l.get('href', '').endswith('.HDF5')), None)
        print(f"Granule: {e.get('title')} | start: {e.get('time_start')} | link: {hdf5_link}")

if __name__ == '__main__':
    print("Collections:")
    search_collections()
    print("\nGranules GPM_3IMERGHDF (V07):")
    search_granules("GPM_3IMERGHDF", "2015-11-30T00:00:00Z", "2015-12-05T00:00:00Z")
