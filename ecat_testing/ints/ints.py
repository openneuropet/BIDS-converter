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


def create_sample_bytes(destination_file='python_sample_bytes.bytes'):
    """
    Create a file with two 16-bit integers, one positive and one negative.

    :param destination_file: _description_, defaults to 'sample_bytes.bytes'
    :type destination_file: str, optional
    """
    bytes_to_write = [-32768, 32767]
    with open(destination_file, 'wb') as file:
        byte_order = 'big'
        signed = True
        for b in bytes_to_write:
            print(f"Writing {b} to {destination_file}, byte order: {byte_order}, signed: {signed}")
            file.write(b.to_bytes(2, byteorder=byte_order, signed=True))


def read_bytes(file_name='python_sample_bytes.bytes'):
    """
    Open a byte file and read in the bytes without any extra fluff.

    :param file_name: the file to read bytes from, defaults to 'sample_bytes.bytes'
    :type file_name: str, optional
    :return: the bytes read from the file
    :rtype: bytes
    """
    with open(file_name, 'rb') as file:
        bytes_read = file.read()
    print(f"Read these bytes from {file_name}: {bytes_read}")
    return bytes_read


# create the bytes to be read
create_sample_bytes()
# read the bytes
read_nums = read_bytes()

# these are some of the datatypes we wish to test with numpy
# i2 = integer 16 signed, >i2 = integer 16 big endian signed, H = integer 16 unsigned
dtypes = ['i2', '>i2', 'H']

# create a dictionary to hold the arrays we create with numpy
arrays_by_dtype = {}

# iterate through the datatypes and create arrays with numpy
for d in dtypes:
    numpy_int16 = numpy.frombuffer(read_nums, dtype=d)
    print(f"Reading bytes with numpy given datatype: {d}\nArray is listing this as : {numpy_int16.dtype} {numpy_int16}")
    arrays_by_dtype[d] = numpy_int16

print(f"Arrays by dtype: {arrays_by_dtype}")

# next we go through the same steps that the ecat converter does but in miniature since a 1x2 array is easier for us
# hairless apes to comprehend than a near as enough to make no difference N dimensional array

# scale it the calibration factor we have been dealing with in these wustl ecats is 0.7203709074867248
calibration_factor = 0.7203709074867248

scaled_arrays = {}

for k, v in arrays_by_dtype.items():
    # try recasting the  scaled array after the multiplication
    scaled_arrays[k] = v * calibration_factor

print(f"These are the arrays after being scaled by {calibration_factor}: {scaled_arrays}")

# write these out to nifti's
for k, v in scaled_arrays.items():
    nifti = nibabel.Nifti1Image(v, affine=numpy.eye(4))
    input_data_type = v.dtype
    nibabel_data_type = nifti.get_data_dtype()
    print(f"Input data type: {input_data_type}, Nibabel data type: {nibabel_data_type}")
    nibabel.save(nifti, f"nibabel_{k}.nii.gz")
    print(f"Saved array to numpy_{k}.nii.gz")
    print(f"loading that array results in the following: {nibabel.load(f'nibabel_{k}.nii.gz').get_fdata()}")

# what happens if we don't scale the arrays and write them to nifti
for k, v in arrays_by_dtype.items():
    input_data_type = v.dtype
    nibabel_data_type = nifti.get_data_dtype()
    print(f"Input data type: {input_data_type}, Nibabel data type: {nibabel_data_type}")
    nibabel.save(nifti, f"nibabel_{k}_unscaled.nii.gz")
    print(f"Saved array to numpy_{k}_unscaled.nii.gz")
    print(f"loading that array results in the following: {nibabel.load(f'nibabel_{k}_unscaled.nii.gz').get_fdata()}")
