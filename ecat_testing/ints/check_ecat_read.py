import numpy
import nibabel
import dotenv
import os



# load the environment variables
dotenv.load_dotenv('variables.env')

# get the path to the input ecat file from the environment variables
ecat_file = os.getenv('WELL_BEHAVED_ECAT_FILE')
wustl_fbp_ecat=os.getenv('WUSTL_FBP_ECAT')
wustl_osem_ecat=os.getenv('WUSTL_OSEM_ECAT')