"""
Contains class ecat2ii, used to write ecat information out to a nifti file, depends on
`nibabel <https://nipy.org/nibabel/>`_ and  :func:`pypet2bids.read_ecat.read_ecat`.

| *Authors: Anthony Galassi*
| *Copyright OpenNeuroPET team*
"""

import datetime
import nibabel
import numpy
import pathlib
from pypet2bids.read_ecat import (
    read_ecat,
    code_dir,
)  # we use code_dir for ecat debugging
import os
import pickle
import logging

try:
    import helper_functions
except ModuleNotFoundError:
    import pypet2bids.helper_functions as helper_functions


# debug variable
# save steps for debugging, for mor infor see ecat_testing/README.md
ecat_save_steps = os.environ.get("ECAT_SAVE_STEPS", 0)
if ecat_save_steps == "1":
    # check to see if the code directory is available, if it's not create it and
    # the steps dir to save outputs created if ecat_save_steps is set to 1
    steps_dir = code_dir.parent / "ecat_testing" / "steps"
    if not steps_dir.is_dir():
        os.makedirs(code_dir.parent / "ecat_testing" / "steps", exist_ok=True)

logger = logging.getLogger("pypet2bids")


def ecat2nii(
    ecat_main_header=None,
    ecat_subheaders=None,
    ecat_pixel_data=None,
    ecat_file=None,
    nifti_file: str = "",
    sif_out=False,
    affine=None,
    save_binary=False,
    **kwargs,
):
    """
    Converts an ECAT file into a nifti and a sidecar json, used in conjunction with
    :func:`pypet2bids.read_ecat.read_ecat`

    :param ecat_main_header: the main header of an ECAT file
    :param ecat_subheaders: the subheaders for each frame of the ECAT file
    :param ecat_pixel_data: the imaging/pixel data from the ECAT file
    :param ecat_file: the path to the ECAT file, required and used to create .nii and .json output files
    :param nifti_file: the desired output path of the nifti file
    :param sif_out: outputs a .sif file containing the images pixel data
    :param affine: a user supplied affine, this is gathered from the ECAT if not supplied.
    :param save_binary: dumps a pickled ECAT object, you probably shouldn't be using this.
    :param kwargs: additional key value pairs that one wishes to add to the sidecar json accompanying a converted ECAT
        nii image
    :return: a nibabel nifti object if one wishes to muddle with the object in python and not in a .nii file

    """

    # if a nifti file/path is not included write a nifti next to the ecat file
    if not nifti_file:
        nifti_file = os.path.splitext(ecat_file)[0] + ".nii"
    else:
        nifti_file = nifti_file

    if not pathlib.Path(nifti_file).parent.exists():
        pathlib.Path(nifti_file).parent.mkdir(parents=True, exist_ok=True)

    # collect the output folder from the nifti path will use for .sif files
    output_folder = pathlib.Path(nifti_file).parent
    nifti_file_w_out_extension = os.path.splitext(str(pathlib.Path(nifti_file).name))[0]

    # if already read nifti file skip re-reading
    if (
        ecat_main_header is None
        and ecat_subheaders is None
        and ecat_pixel_data is None
        and ecat_file
    ):
        # collect ecat_file
        main_header, sub_headers, data = read_ecat(ecat_file=ecat_file)
    elif (
        ecat_file is None
        and type(ecat_main_header) is dict
        and type(ecat_subheaders) is list
        and type(ecat_pixel_data) is numpy.ndarray
    ):
        main_header, sub_headers, data = (
            ecat_main_header,
            ecat_subheaders,
            ecat_pixel_data,
        )
    else:
        raise Exception(
            "Must pass in filepath for ECAT file or "
            "(ecat_main_header, ecat_subheaders, and ecat_pixel data "
            f"got ecat_file={ecat_file}, type(ecat_main_header)={type(ecat_main_header)}, "
            f"type(ecat_subheaders)={type(ecat_subheaders)}, "
            f"type(ecat_pixel_data)={type(ecat_pixel_data)} instead."
        )

    # debug step #6 view data as passed to ecat2nii method
    if ecat_save_steps == "1":
        # collect only the first, middle, and last frames from pixel_data_matrix_4d as first, middle, and last
        # frames are typically the most interesting
        frames = [0, len(data) // 2, -1]
        frames_to_record = []
        for f in frames:
            frames_to_record.append(data[:, :, :, f])

        # now collect a single 2d slice from the "middle" of the 3d frames in frames_to_record
        slice_to_record = []
        for index, frame in enumerate(frames_to_record):
            numpy.savetxt(
                steps_dir / f"6_ecat2nii_python_{index}.tsv",
                frames_to_record[index][:, :, frames_to_record[index].shape[2] // 2],
                delimiter="\t",
                fmt="%s",
            )

        helper_functions.first_middle_last_frames_to_text(
            four_d_array_like_object=data,
            output_folder=steps_dir,
            step_name="6_ecat2nii_python",
        )

    # set the byte order and the pixel data type from the input array
    pixel_data_type = data.dtype

    # check for TimeZero supplied via kwargs
    if kwargs.get("TimeZero", None):
        TimeZero = kwargs["TimeZero"]
    else:
        logger.warning(
            "Metadata TimeZero is missing -- set to ScanStart or empty to use the scanning time as "
            "injection time"
        )

    # get image shape
    img_shape = data.shape
    shape_from_headers = (
        sub_headers[0]["X_DIMENSION"],
        sub_headers[0]["Y_DIMENSION"],
        sub_headers[0]["Z_DIMENSION"],
        main_header["NUM_FRAMES"],
    )

    # make sure number of data elements matches frame number
    single_frame = False
    if img_shape[3] == 1 and img_shape[0:2] == shape_from_headers[0:2]:
        single_frame = True
    if img_shape != shape_from_headers and not single_frame:
        raise Exception(
            f"Mis-match between expected X,Y,Z, and Num. Frames dimensions ({shape_from_headers} obtained from headers"
            f"and shape of imaging data ({img_shape}"
        )

    # format data into acceptable shape for nibabel, by first creating empty matrix
    img_temp = numpy.zeros(
        shape=(
            sub_headers[0]["X_DIMENSION"],
            sub_headers[0]["Y_DIMENSION"],
            sub_headers[0]["Z_DIMENSION"],
            main_header["NUM_FRAMES"],
        ),
        dtype=">f4",
    )

    # collect timing information
    start, delta = [], []

    # collect prompts and randoms
    prompts, randoms = [], []

    # load frame data into img temp
    for index in reversed(
        range(img_shape[3])
    ):  # Don't throw stones working from existing matlab code
        print(f"Loading frame {index + 1}")
        img_temp[:, :, :, index] = numpy.flip(
            numpy.flip(
                numpy.flip(
                    data[:, :, :, index] * sub_headers[index]["SCALE_FACTOR"], 1
                ),
                2,
            ),
            0,
        )
        start.append(sub_headers[index]["FRAME_START_TIME"] * 60)  # scale to per minute
        delta.append(sub_headers[index]["FRAME_DURATION"] * 60)  # scale to per minute

        if main_header.get("SW_VERSION", 0) >= 73:
            # scale both to per minute
            prompts.append(
                sub_headers[index]["PROMPT_RATE"]
                * sub_headers[index]["FRAME_DURATION"]
                * 60
            )
            randoms.append(
                sub_headers[index]["RANDOM_RATE"]
                * sub_headers[index]["FRAME_DURATION"]
                * 60
            )
        else:
            # this field is not available in ecat 7.2
            prompts.append(0)
            randoms.append(0)

    # debug step #7 view data after flipping into nifti space/orientation
    if ecat_save_steps == "1":
        helper_functions.first_middle_last_frames_to_text(
            four_d_array_like_object=img_temp,
            output_folder=steps_dir,
            step_name="7_flip_ecat2nii_python",
        )

    # so the only real difference between the matlab code and the python code is that that we aren't manually
    # scaling the date to 16 bit integers.
    rg = img_temp.max() - img_temp.min()
    if rg != 32767:
        max_img = img_temp.max()
        img_temp = img_temp / max_img * 32767
        sca = max_img / 32767
        min_img = img_temp.min()
        if min_img < -32768:
            img_temp = img_temp / (min_img * -32768)
            sca = sca * (min_img * -32768)
    if ecat_save_steps == "1":
        with open(os.path.join(steps_dir, "8.5_sca.txt"), "w") as sca_file:
            sca_file.write(f"Scaling factor: {sca}\n")
            sca_file.write(
                f"Scaling factor * ECAT Cal Factor: {sca * main_header['ECAT_CALIBRATION_FACTOR']}\n"
            )

    # scale image to 16 bit
    final_image = img_temp.astype(numpy.single)

    # debug step 8 check after "rescaling" to 16 bit
    if ecat_save_steps == "1":
        helper_functions.first_middle_last_frames_to_text(
            four_d_array_like_object=final_image,
            output_folder=steps_dir,
            step_name="8_rescale_to_16_ecat2nii_python",
        )

    ecat_cal_units = main_header[
        "CALIBRATION_UNITS"
    ]  # Header field designating whether data has already been calibrated
    if ecat_cal_units == 1:  # Calibrate if it hasn't been already
        final_image = (
            numpy.round(final_image) * main_header["ECAT_CALIBRATION_FACTOR"] * sca
        )
        # this debug step may not execute if we're not calibrating the scan, but that's okay
        if ecat_save_steps == "1":
            helper_functions.first_middle_last_frames_to_text(
                four_d_array_like_object=final_image,
                output_folder=steps_dir,
                step_name="9_scal_cal_units_ecat2nii_python",
            )
    else:  # And don't calibrate if CALIBRATION_UNITS is anything else but 1
        final_image = numpy.round(final_image) * sca

    qoffset_x = -1 * (
        (
            (sub_headers[0]["X_DIMENSION"] * sub_headers[0]["X_PIXEL_SIZE"] * 10 / 2)
            - sub_headers[0]["X_PIXEL_SIZE"] * 5
        )
    )

    qoffset_y = -1 * (
        (
            (sub_headers[0]["Y_DIMENSION"] * sub_headers[0]["Y_PIXEL_SIZE"] * 10 / 2)
            - sub_headers[0]["Y_PIXEL_SIZE"] * 5
        )
    )

    qoffset_z = -1 * (
        (
            (sub_headers[0]["Z_DIMENSION"] * sub_headers[0]["Z_PIXEL_SIZE"] * 10 / 2)
            - sub_headers[0]["Z_PIXEL_SIZE"] * 5
        )
    )

    # build affine if it's not included in function call
    if not affine:
        mat = (
            numpy.diag(
                [
                    sub_headers[0]["X_PIXEL_SIZE"],
                    sub_headers[0]["Y_PIXEL_SIZE"],
                    sub_headers[0]["Z_PIXEL_SIZE"],
                ]
            )
            * 10
        )
        affine = nibabel.affines.from_matvec(mat, [qoffset_x, qoffset_y, qoffset_z])

    img_nii = nibabel.Nifti1Image(final_image, affine=affine)

    # debug step 10, check to see what's happened after we've converted our numpy array in to a nibabel object
    if ecat_save_steps == "1":
        helper_functions.first_middle_last_frames_to_text(
            four_d_array_like_object=img_nii.dataobj,
            output_folder=steps_dir,
            step_name="10_save_nii_ecat2nii_python",
        )

    img_nii.header.set_slope_inter(slope=1, inter=0)
    img_nii.header.set_xyzt_units("mm", "sec")
    img_nii.header.set_qform(affine, code=1)
    img_nii.header.set_sform(affine, code=1)
    # No setter methods for these
    img_nii.header["cal_max"] = final_image.max()
    img_nii.header["cal_min"] = final_image.min()
    img_nii.header["descrip"] = "OpenNeuroPET ecat2nii.py conversion"

    nibabel.save(img_nii, nifti_file)

    # run step 11 in debug
    if ecat_save_steps == "1":
        # load nifti file with nibabel
        written_img_nii = nibabel.load(nifti_file)

        helper_functions.first_middle_last_frames_to_text(
            four_d_array_like_object=written_img_nii.dataobj,
            output_folder=steps_dir,
            step_name="11_read_saved_nii_python",
        )

    # used for testing veracity of nibabel read and write.
    if save_binary:
        pickle.dump(img_nii, open(nifti_file + ".pickle", "wb"))

    # write out timing file
    if sif_out:
        with open(
            os.path.join(output_folder, nifti_file_w_out_extension + ".sif"), "w"
        ) as sif_file:
            scantime = datetime.datetime.fromtimestamp(main_header["SCAN_START_TIME"])
            scantime = scantime.astimezone().isoformat()
            sif_file.write(f"{scantime} {len(start)} 4 1\n")
            for index in reversed(range(len(start))):
                start_i = round(start[index])
                start_i_plus_delta_i = start_i + round(delta[index])
                prompt = round(prompts[index])
                random = round(randoms[index])
                output_string = f"{start_i} {start_i_plus_delta_i} {prompt} {random}\n"
                sif_file.write(output_string)

    return img_nii
