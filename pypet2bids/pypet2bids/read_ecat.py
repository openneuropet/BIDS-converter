"""
This module contains methods used to read ecat files (\*.v), the primary method pulled/imported from this module
is read_ecat which returns the contents of a singular ecat file divided into three parts:

- main header
- subheaders
- pixel data

The other functions primarily operate bitwise, so it's best not to use them outside of this module, unless you are a
glutton or twisted in that sort of way.

:Authors: Anthony Galassi
:Copyright: Open NeuroPET team

"""

import json
import os.path
import struct
from os import path
from os.path import join
import pathlib
import re
import numpy
from pypet2bids.helper_functions import decompress, first_middle_last_frames_to_text

parent_dir = pathlib.Path(__file__).parent.resolve()
code_dir = parent_dir.parent
data_dir = code_dir.parent

# debug variable
# save steps for debugging for more info see ecat_testing/README.md
ecat_save_steps = os.environ.get("ECAT_SAVE_STEPS", 0)
if ecat_save_steps == "1":
    # check to see if the code directory is available, if it's not create it and
    # the steps dir to save outputs created if ecat_save_steps is set to 1
    steps_dir = code_dir.parent / "ecat_testing" / "steps"
    if not steps_dir.is_dir():
        os.makedirs(code_dir.parent / "ecat_testing" / "steps", exist_ok=True)


# collect ecat header maps, this program will not work without these as ECAT data varies in the byte location of its
# data depending on the version of ECAT it was formatted with.
try:
    with open(join(parent_dir, "ecat_headers.json"), "r") as infile:
        ecat_header_maps = json.load(infile)
except FileNotFoundError:
    raise Exception(
        "Unable to load header definitions and map from ecat_headers.json. Aborting."
    )


# noinspection PyShadowingNames
def get_ecat_bytes(path_to_ecat: str):
    """
    Opens an ecat file and reads the entry file into memory to return a bytes object
    not terribly memory efficient for large or parallel reading of ecat files.

    :param path_to_ecat: path to an ecat file, however will literally open any file an read it
        in as bytes.
    :return: a bytes object
    """
    # check if file exists
    if path.isfile(path_to_ecat):
        with open(path_to_ecat, "rb") as infile:
            ecat_bytes = infile.read()
    else:
        raise Exception(f"No such file found at {path_to_ecat}")

    return ecat_bytes


def read_bytes(path_to_bytes: str, byte_start: int, byte_stop: int = -1):
    """
    Open a file at path to bytes and reads in the information byte by byte.

    :param path_to_bytes: Path to file to read
    :param byte_start: Position to place the seek head at before reading bytes
    :param byte_stop: Position to stop reading bytes at
    :return: the bytes located at the position sought when invoking this function.
    """
    if not os.path.isfile(path_to_bytes):
        raise Exception(f"{path_to_bytes} is not a valid file.")

    # open that file
    bytes_to_read = open(path_to_bytes, "rb")

    # move to start byte
    bytes_to_read.seek(byte_start, 0)

    # read a section of bytes from bytestart to byte stop
    byte_width = byte_stop
    sought_bytes = bytes_to_read.read(byte_width)

    bytes_to_read.close()
    return sought_bytes


def collect_specific_bytes(
    bytes_object: bytes, start_position: int = 0, width: int = 0
):
    """
    Collects specific bytes within a bytes object.

    :param bytes_object: an opened bytes object
    :param start_position: the position to start to read at
    :param width: how far to read from the start position
        2 -> end of file/object
    :return: the bytes starting at position
    """
    # navigate to byte position
    content = bytes_object[start_position : start_position + width]
    return {"content": content, "new_position": start_position + width}


def get_buffer_size(data_type: str, variable_name: str):
    """
    Determine the byte width of a variable as defined in the ecat_headers.json
    such that Fill(6) will return 6

    :param data_type:
    :param variable_name:
    :return: the number of bytes to expand a buffer to
    """
    first_split = variable_name.split("(")
    if len(first_split) == 2:
        fill_scalar = int(first_split[1][:-1])
    else:
        fill_scalar = 1
    scalar = int(re.findall(r"\d+", data_type)[0]) * fill_scalar

    return scalar


def get_header_data(
    header_data_map: dict, ecat_file: str = "", byte_offset: int = 0, clean=True
):
    """
    ECAT header data is contained in json files translated from ECAT documentation provided via the Turku PET Inst.
    For machine and human readability the original Siemens PDF/Scanned ECAT file documentation has been rewritten into
    json to provide easy access to byte position, byte width, variable name, and byte data type. Json's including this
    header information are sub-divided into ECAT versions with sub-dictionaries corresponding to each imaging type as
    mentioned in the original ECAT spec.

    :param header_data_map: schema for reading in header data, this is stored in dictionary that is read in from a
           json file.
    :param ecat_file: path to an ecat file, file is opened and byte blocks containing header data are then extracted,
           read, and cleaned into python float, int, or list data types
    :param byte_offset: off set from the head of the file to read from
    :param clean: Whether to remove byte padding or not, if not provided strings will include padding w/ \0x bytes and
           lists/arrays of data will be returned as tuples instead of lists. Uncleaned data will be of format b''.
    :return: a dictionary with variable names of header fields as keys and cleaned/uncleaned header fields as values
    """
    header = {}

    for value in header_data_map:
        byte_position, variable_name, struct_fmt = (
            value["byte"],
            value["variable_name"],
            ">" + value["struct"],
        )
        byte_width = struct.calcsize(struct_fmt)
        relative_byte_position = byte_position + byte_offset
        raw_bytes = read_bytes(ecat_file, relative_byte_position, byte_width)
        header[variable_name] = struct.unpack(struct_fmt, raw_bytes)
        if clean and "fill" not in variable_name.lower():
            header[variable_name] = filter_bytes(header[variable_name], struct_fmt)
        if "comment" in value and "msec" in value["comment"]:
            # for entries that are in msec, convert to sec for PET BIDS json
            header[variable_name] /= 1000
        read_head_position = relative_byte_position + byte_width

    return header, read_head_position


def filter_bytes(unfiltered: bytes, struct_fmt: str):
    """
    Cleans up byte strings and bytes types into python int, float, string, and list data types, additionally
    struct.unpack returns a tuple object even if only a single value is available, this function determines when to
    return a single value or a list of values based on the contents of the unfiltered object.

    :param unfiltered: a raw bytes type object
    :param struct_fmt: the c struct type of the object
    :return: a cleaned python int, float, string, or list
    """
    if len(unfiltered) == 1:
        unfiltered = unfiltered[0]
    elif len(unfiltered) > 1:
        unfiltered = list(unfiltered)
    if "s" in struct_fmt:
        filtered = str(bytes(filter(None, unfiltered)), "UTF-8")
    else:
        filtered = unfiltered
    return filtered


def get_directory_data(byte_block: bytes, ecat_file: str, return_raw: bool = False):
    """
    Collects the directory data within an ECAT file. The directory data refers to the 512 byte table that describes the
    byte location of each frame, subheader, number of frames, and additional directory tables within the file.

    :param byte_block: A block of file bytes to convert into a 2 dimensional numpy array.
    :param ecat_file: the path to the ecat file
    :param return_raw: return the directory tables as extracted, if left False this will return the directory tables
           combined into a single table. The single table is all that is needed in order to read information in from an
           ECAT.
    :return: Individual tables corresponding to up to 31 frames each or a combined directory table consisting of no
             more columns than than are number of frames in the image/PET scan.
    """
    directory = None  # used to keep track of state in the event of a directory spanning more than one 512 byte block
    raw = []
    while True:
        # The exit conditions for this loop are below
        # if [4,1] of the directory is 0 break as there are 31 or less frames in this 512 byte buffer
        # if [2,1] of the directory is 2 break ????, up for interpretation as to the exact meaning but,
        # observed to signal the end of an additional 512 byte block/buffer when the number of frames
        # exceeds 31

        read_byte_array = numpy.frombuffer(
            byte_block, dtype=numpy.dtype(">i4"), count=-1
        )
        # reshape 1d array into 2d, a 4 row by 32 column table is expected
        reshaped = numpy.transpose(numpy.reshape(read_byte_array, (-1, 4)))

        raw.append(reshaped)

        # chop off columns after 32, rows after 32 appear to be noise
        reshaped = reshaped[:, 0 : read_byte_array[3] + 1]
        # get directory size/number of frames in dir from 1st column 4th row of the array in the buffer
        directory_size = reshaped[3, 0]
        if directory_size == 0:
            break
        # on the first pass do this
        if directory is None:
            directory = reshaped[:, 1 : directory_size + 1]
        else:
            directory = numpy.append(
                directory, reshaped[:, 1 : directory_size + 1], axis=1
            )
        # determine if this is the last directory by examining the 2nd row of the first column of the buffer
        next_directory_position = reshaped[1, 0]
        if next_directory_position == 2:
            break
        # looks like there is more directory to read, collect some more bytes
        byte_block = read_bytes(
            path_to_bytes=ecat_file,
            byte_start=(next_directory_position - 1) * 512,
            byte_stop=512,
        )

    # sort the directory contents as they're sometimes out of order
    sorted_directory = directory[:, directory[0].argsort()]

    if return_raw:
        return raw
    else:
        return sorted_directory


def read_ecat(
    ecat_file: str, calibrated: bool = False, collect_pixel_data: bool = True
):
    """
    Reads in an ecat file and collects the main header data, subheader data, and imagining data.

    :param ecat_file: path to an ecat file, does not handle compression currently
    :param calibrated: if True, will scale the raw imaging data by the SCALE_FACTOR in the subheader and
    :param collect_pixel_data: By default collects the entire ecat, can be passed false to only return headers
        CALIBRATION_FACTOR in the main header

    :return: main_header, a list of subheaders for each frame, the imagining data from the subheaders

    """
    if ".gz" in ecat_file:
        ecat_file = decompress(ecat_file)

    # try to determine what type of ecat this is
    possible_ecat_headers = {}
    for entry, dictionary in ecat_header_maps["ecat_headers"].items():
        possible_ecat_headers[entry] = dictionary["mainheader"]

    # set byte order
    byte_order = ">"

    confirmed_version = None
    for version, dictionary in possible_ecat_headers.items():
        try:
            possible_header, _ = get_header_data(dictionary, ecat_file)
            if version == str(possible_header["SW_VERSION"]):
                confirmed_version = version
                break
        except UnicodeDecodeError:
            continue

    if not confirmed_version:
        raise Exception(
            f"Unable to determine ECAT File Type from these types {possible_ecat_headers.keys()}"
        )

    ecat_main_header = ecat_header_maps["ecat_headers"][confirmed_version]["mainheader"]

    main_header, read_to = get_header_data(ecat_main_header, ecat_file)

    if ecat_save_steps == "1":
        with open(steps_dir / "1_read_mh_ecat_python.json", "w") as outfile:
            json.dump(main_header, outfile)
    """
    Some notes about the file directory/sorted directory:
    
    Comments referencing matrix/table indexing may vary by +-1 in relation to code written.
    Python is 0 indexed by default so it can be taken as truth w/ relation to element location.
    Deviation from this convention are intended to clarify what is happening to a human reader
    although we are aware that this most likely has the opposite effect. 

    The first or 0th column of the file directory correspond to the nature of the directory itself:
    row 0: ??? No idea, some integer
    row 1: Byte position of this table/directory
    row 2: not sure in testing it seems to be 0 most times..
    row 3: The number of frames/additional columns in the file. If the number of columns of this array
    is n, it would contain n-1 frames. 

    The values in sorted_directory correspond to the following for all columns except the first column
    row 0: Not sure, but we sort on this, perhaps it's the frame start time
    row 1: the start byte block position of the frame data
    row 2: end byte block position of the frame data
    row 3: ??? Number of frames contained in w/ in the byte blocks between row 1 and 2?
    """

    # Collecting First Part of File Directory/Index this Directory lies directly after the main header byte block
    next_block = read_bytes(
        path_to_bytes=ecat_file, byte_start=read_to, byte_stop=read_to + 512
    )

    directory = get_directory_data(next_block, ecat_file)

    # determine subheader type by checking main header
    subheader_type_number = main_header["FILE_TYPE"]

    """
    ECAT 7.2 Only
    Subheader types correspond to these enumerated types as defined below:
    00 = unknown, 
    01 = Sinogram, 
    02 = Image - 16, 
    03 = Attenuation Correction, 
    04 = Normalization, 
    05 = PolarMap, 
    06 = Volume 8, 
    07 = Volume 16, 
    08 = Projection 8, 
    09 = Projection 16, 
    10 = Image 8, 
    11 = 3D Sinogram 16, 
    12 = 3D Sinogram 8, 
    13 = 3D Normalization, 
    14 = 3D Sinogram Fit)

    Presently, only types 03, 05, 07, 11, and 13 correspond to known subheader types for 72. If the
    value in FILE_TYPE is outside of this range the subheaders will not be read and this will
    raise an exception.
    
    ECAT 7.3 Only
    00 = unknown
    01 = unknown
    02 = unknown
    03 = Attenuation Correction
    04 = unknown
    05 = unknown
    06 = unknown
    07 = Volume 16
    08 = unknown
    09 = unknown
    10 = unknown
    11 = 3D Sinogram 16 
    """

    # collect the bytes map file for the designated subheader, note some are not supported.
    subheader_map = ecat_header_maps["ecat_headers"][confirmed_version][
        str(subheader_type_number)
    ]

    if not subheader_map:
        raise Exception(f"Unsupported data type: {subheader_type_number}")

    # collect subheaders and pixel data
    subheaders, data = [], []
    for i in range(len(directory.T)):
        frame_number = i + 1
        if collect_pixel_data:
            print(f"Reading subheader from frame {frame_number}")

        # collect frame info/column
        frame_info = directory[:, i]
        frame_start = frame_info[1]
        frame_stop = frame_info[2]

        frame_start_byte_position = 512 * (frame_start - 1)  # sure why not
        # read subheader
        subheader, byte_position = get_header_data(
            subheader_map, ecat_file, byte_offset=frame_start_byte_position
        )

        if collect_pixel_data:
            # collect pixel data from file
            pixel_data = read_bytes(
                path_to_bytes=ecat_file,
                byte_start=512 * frame_start,
                byte_stop=512 * frame_stop,
            )

            # calculate size of matrix for pixel data, may vary depending on image type (polar, 3d, etc.)
            if subheader_type_number == 7:
                image_size = [
                    subheader["X_DIMENSION"],
                    subheader["Y_DIMENSION"],
                    subheader["Z_DIMENSION"],
                ]
                # check subheader for pixel datatype
                dt_val = subheader["DATA_TYPE"]
                if dt_val == 5:
                    formatting = ">f4"
                    pixel_data_type = numpy.dtype(formatting)
                elif dt_val == 6:
                    # >H is unsigned short e.g. >u2, reverting to int16 e.g. i2 to align with commit 9beee53
                    pixel_data_type = ">i2"
                else:
                    raise ValueError(
                        f"Unable to determine pixel data type from value: {dt_val} extracted from {subheader}"
                    )
                # read it into a one dimensional matrix
                pixel_data_matrix_3d = numpy.frombuffer(
                    pixel_data,
                    dtype=pixel_data_type,
                    count=image_size[0] * image_size[1] * image_size[2],
                ).reshape(*image_size, order="F")
                # pixel_data_matrix_3d.newbyteorder(byte_order)

                if ecat_save_steps == "1":
                    with open(
                        steps_dir / f"4_determine_data_type_python.json", "w"
                    ) as outfile:
                        json.dump(
                            {"DATA_TYPE": dt_val, "formatting": pixel_data_type},
                            outfile,
                        )

            else:
                raise Exception(
                    f"Unable to determine frame image size, unsupported image type {subheader_type_number}"
                )

            # we assume the user doesn't want to do multiplication to adjust for calibration here
            if calibrated:
                calibration_factor = (
                    subheader["SCALE_FACTOR"] * main_header["ECAT_CALIBRATION_FACTOR"]
                )
                calibrated_pixel_data_matrix_3d = (
                    calibration_factor * pixel_data_matrix_3d
                )
                data.append(calibrated_pixel_data_matrix_3d)
            else:
                data.append(pixel_data_matrix_3d)
        else:
            data = None

        subheaders.append(subheader)

        if ecat_save_steps == "1":
            with open(steps_dir / f"2_read_sh_ecat_python.json", "w") as outfile:
                json.dump({"subheaders": subheaders}, outfile)

    if collect_pixel_data:
        # return 4d array instead of list of 3d arrays
        pixel_data_matrix_4d = numpy.zeros(
            tuple(image_size + [len(data)]), dtype=numpy.dtype(pixel_data_type)
        )
        for index, frame in enumerate(data):
            pixel_data_matrix_4d[:, :, :, index] = frame

        if ecat_save_steps == "1":

            # write out the endianess and datatype of the pixel data matrix
            step_3_dict = {
                "datatype": pixel_data_matrix_4d.dtype.name,
                "endianness": pixel_data_matrix_4d.dtype.byteorder,
            }

            with open(steps_dir / f"3_determine_data_type_python.json", "w") as outfile:
                json.dump(step_3_dict, outfile)

            # record out step 4
            first_middle_last_frames_to_text(
                four_d_array_like_object=pixel_data_matrix_4d,
                output_folder=steps_dir,
                step_name="4_read_img_ecat_python",
            )

            # record out step 5
            if calibrated:
                first_middle_last_frames_to_text(
                    four_d_array_like_object=calibrated_pixel_data_matrix_3d,
                    output_folder=steps_dir,
                    step_name="5_scale_img_ecat_python",
                )

    else:
        pixel_data_matrix_4d = None

    return main_header, subheaders, pixel_data_matrix_4d
