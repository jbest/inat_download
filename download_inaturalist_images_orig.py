"""
This script downloads all images associated with iNaturalist observation 
records. Observation data are exported from iNaturalist with iNaturalist
Export CSV functionality. For more details, see 
https://github.com/amdevine/ggi-gardens-photos

Required input: 
    - observations.csv

Outputs:
    - images folder containing downloaded jpg images
    - image_metadata.csv (image metadata for downloaded images)

Command line/terminal usage:
    python download_inaturalist_images.py
    (or python3 download_inaturalist_images.py)
"""

# Import the requisite Python libraries
import os, requests, time, urllib.request
import pandas as pd

collector_numbers = dict()

def retrieve_image_letter(cn):
    """Returns and updates the latest letter associated with a collector number"""
    if collector_numbers.get(cn, None):
        collector_numbers[cn] = chr(ord(collector_numbers[cn]) + 1)
    else:
        collector_numbers[cn] = 'A'
    return collector_numbers[cn]

def retrieve_collector_number(obs):
    """Iterates through observation fields to find Collector Number"""
    obsfields = obs.get('observation_field_values', [])
    for field in obsfields:
        if field.get('observation_field', {}).get('name', '') == 'Collector Number':
            return field.get('value', 'No_Collector_Number').replace(" ", "_")
    return "No_Collector_Number"

# Read observations.csv and extract observation IDs
try:
    observations = pd.read_csv('observations.csv')
except FileNotFoundError:
    print("Could not find observations.csv. Program is now quitting.")
    exit()
obs_ids = list(observations['id'])

# For each observation, use the API to retrieve the associated image data
# original.jpg is not provided in the API metadata, but it does seem to work
# to get the original image size
print("Retrieving photo data for {} observations".format(len(obs_ids)))
images = []
obs_counter = 0
for idno in obs_ids:
    url = "https://www.inaturalist.org/observations/{}.json".format(idno)
    obs = requests.get(url).json()
    photos = obs.get('observation_photos', [])
    col_num = retrieve_collector_number(obs)
    for photo in photos:
        photo_data = {'observation_id': photo.get('observation_id', None)}
        photo_data.update(photo.get('photo', {}))
        photo_data['original_size_url'] = photo_data.get('large_url', '').replace('large', 'original')
        photo_data['collector_number'] = retrieve_collector_number(obs)
        if col_num == 'No_Collector_Number':
            photo_data['photo_identifier'] = photo_data['id']
        else:
            photo_data['photo_identifier'] = retrieve_image_letter(photo_data['collector_number'])
        images.append(photo_data)
    time.sleep(1) # Rate limit 1 request per second
    
    obs_counter += 1
    if obs_counter % 10 == 0:
        print("{} observations processed, {} total photo data retrieved".format(obs_counter, len(images)))
print("Photo retrieval complete; {} observations processed, {} total photo data retrieved".format(obs_counter, len(images)))

# Export retrieved photo metadata as a CSV file

keep_columns = [
    'observation_id', 'id', 'collector_number', 'photo_identifier', 
    'created_at', 'updated_at', 
    'native_page_url', 'native_username', 'license', 'subtype', 
    'native_original_image_url', 
    'license_code', 'attribution', 'license_name', 'license_url', 
    'type', 'original_size_url'
]

rename_columns = {
    "id": "photo_id", 
    "native_page_url": "inaturalist_page_url",
    "native_username": "inaturalist_username", 
    "native_original_image_url": "original_image_url",
    "original_size_url": "image_url"
}

images_df = pd.DataFrame(images)
images_df = images_df[keep_columns]
images_df = images_df.rename(columns=rename_columns)
print("Image metadata outputted to image_metadata.csv")

# Create images directory
try:
    os.mkdir('images')
    print("Created images directory.")
except FileExistsError:
    print('Images directory already exists, using existing images directory')

# For every photo retrieved via the API, download the photo in its original 
# size to the images directory
image_counter = 0
print("Retrieving {} images".format(len(images)))
for image in images:
    coll_no = image.get('collector_number', 'Unknown')
    photo_iden = image.get('photo_identifier', 'Unknown')
    image_name = "images/{}_{}.jpg".format(coll_no, photo_iden)
    image_url = image.get('original_size_url', None)
    if image_url:
        urllib.request.urlretrieve(image_url, image_name)
    
    image_counter += 1
    if image_counter % 10 == 0:
        print("Retrieved {} of {} images".format(image_counter, len(images)))
    time.sleep(1) # Rate limit 1 request per second
print("Download complete, {} of {} images retrieved".format(len(images), len(images)))