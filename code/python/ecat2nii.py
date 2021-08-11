import nibabel
import numpy
import pathlib
from read_ecat import read_ecat
import os
import pickle


def ecat2nii(ecat_main_header=None,
             ecat_subheaders=None,
             ecat_pixel_data=None,
             ecat_file=None,
             nifti_file: str = '',
             sif_out=False,
             affine=None,
             save_binary=False,
             **kwargs):
    # if a nifti file/path is not included write a nifti next to the ecat file
    if not nifti_file:
        nifti_file = os.path.splitext(ecat_file)[0] + ".nii"
    else:
        nifti_file = nifti_file
    # collect the output folder from the nifti path will use for .sif files
    output_folder = pathlib.Path(nifti_file).parent

    # if already read nifti file skip re-reading
    if ecat_main_header is None and ecat_subheaders is None and ecat_pixel_data is None and ecat_file:
        # collect ecat_file
        main_header, sub_headers, data = read_ecat(ecat_file=ecat_file)
    elif ecat_file is None and type(ecat_main_header) is dict and type(ecat_subheaders) is list and type(
            ecat_pixel_data) is numpy.ndarray:
        main_header, sub_headers, data = ecat_main_header, ecat_subheaders, ecat_pixel_data
    else:
        raise Exception("Must pass in filepath for ECAT file or "
                        "(ecat_main_header, ecat_subheaders, and ecat_pixel data "
                        f"got ecat_file={ecat_file}, type(ecat_main_header)={type(ecat_main_header)}, "
                        f"type(ecat_subheaders)={type(ecat_subheaders)}, "
                        f"type(ecat_pixel_data)={type(ecat_pixel_data)} instead.")

    # check for TimeZero supplied via kwargs
    if kwargs.get('TimeZero', None):
        TimeZero = kwargs['TimeZero']
    else:
        print("Metadata TimeZero is missing -- set to ScanStart or empty to use the scanning time as "
              "injection time")

    # get image shape
    img_shape = data.shape
    shape_from_headers = (sub_headers[0]['X_DIMENSION'],
                          sub_headers[0]['Y_DIMENSION'],
                          sub_headers[0]['Z_DIMENSION'],
                          main_header['NUM_FRAMES'])

    # make sure number of data elements matches frame number
    single_frame = False
    if img_shape[3] == 1 and img_shape[0:2] == shape_from_headers[0:2]:
        single_frame = True
    if img_shape != shape_from_headers and not single_frame:
        raise Exception(
            f"Mis-match between expected X,Y,Z, and Num. Frames dimensions ({shape_from_headers} obtained from headers"
            f"and shape of imaging data ({img_shape}")

    # format data into acceptable shape for nibabel, by first creating empty matrix
    img_temp = numpy.zeros(shape=(sub_headers[0]['X_DIMENSION'],
                                  sub_headers[0]['Y_DIMENSION'],
                                  sub_headers[0]['Z_DIMENSION'],
                                  main_header['NUM_FRAMES']),
                           dtype=numpy.dtype('>f4'))

    # collect timing information
    start, delta = [], []

    # collect prompts and randoms
    prompts, randoms = [], []

    # load frame data into img temp
    for index in range(img_shape[3]):
        print(f"Loading frame {index + 1}")
        img_temp[:, :, :, index] = numpy.flip(numpy.flip(numpy.flip(
            data[:, :, :, index].astype(numpy.dtype('>f4')) * sub_headers[index]['SCALE_FACTOR'], 1), 2), 0)
        start.append(sub_headers[index]['FRAME_START_TIME'] * 60)  # scale to per minute
        delta.append(sub_headers[index]['FRAME_DURATION'] * 60)  # scale to per minute

        if main_header.get('SW_VERSION', 0) >= 73:
            # scale both to per minute
            prompts.append(sub_headers[index]['PROMPT_RATE'] * sub_headers[index]['FRAME_DURATION'] * 60)
            randoms.append(sub_headers[index]['RANDOM_RATE'] * sub_headers[index]['FRAME_DURATION'] * 60)
        else:
            # this field is not available in ecat 7.2
            prompts.append(0)
            randoms.append(0)

    # rescale for quantitative PET
    max_image = img_temp.max()
    img_temp = img_temp / (max_image * 32767)
    sca = max_image / 32767
    min_image = img_temp.min()
    if min_image < -32768:
        img_temp = img_temp / (min_image * (-32768))
        sca = sca * min_image / (-32768)

    properly_scaled = img_temp * sca * main_header['ECAT_CALIBRATION_FACTOR']

    img_nii = nibabel.Nifti1Image(properly_scaled, affine=affine)
    # nifti methods that are available to us
    if img_nii.header['sizeof_hdr'] != 348:
        img_nii.header['sizeof_hdr'] = 348
    # img_nii.header['dim_info'] is populated on object creation
    # img_nii.header['dim']  is populated on object creation
    img_nii.header['intent_p1'] = 0
    img_nii.header['intent_p2'] = 0
    img_nii.header['intent_p3'] = 0
    # img_nii.header['datatype'] # created on invocation seems to be 16 or int16
    # img_nii.header['bitpix'] # also automatically created and inferred 32 as of testing w/ cimbi dataset
    # img_nii.header['slice_type'] # defaults to 0
    # img_nii.header['pixdim'] # appears as 1d array of length 8 we rescale this
    img_nii.header['pixdim'] = numpy.array(
        [1,
         sub_headers[0]['X_PIXEL_SIZE'] * 10,
         sub_headers[0]['Y_PIXEL_SIZE'] * 10,
         sub_headers[0]['Z_PIXEL_SIZE'] * 10,
         0,
         0,
         0,
         0])
    img_nii.header['vox_offset'] = 352

    # TODO img_nii.header['scl_slope'] # this is a NaN array by default but apparently it should be the dose calibration factor
    # TODO img_nii.header['scl_inter'] # defaults to NaN array
    img_nii.header['scl_inter'] = 0
    img_nii.header['slice_end'] = 0
    img_nii.header['slice_code'] = 0
    img_nii.header['xyzt_units'] = 10
    img_nii.header['cal_max'] = properly_scaled.min()
    img_nii.header['cal_min'] = properly_scaled.max()
    img_nii.header['slice_duration'] = 0
    img_nii.header['toffset'] = 0
    img_nii.header['descrip'] = "OpenNeuroPET ecat2nii.py conversion"
    # img_nii.header['aux_file'] # ignoring as this is set to '' in matlab
    img_nii.header['qform_code'] = 0
    img_nii.header['sform_code'] = 1  # 0: Arbitrary coordinates;
    # 1: Scanner-based anatomical coordinates;
    # 2: Coordinates aligned to another file's, or to anatomical "truth" (coregistration);
    # 3: Coordinates aligned to Talairach-Tournoux Atlas; 4: MNI 152 normalized coordinates

    img_nii.header['quatern_b'] = 0
    img_nii.header['quatern_c'] = 0
    img_nii.header['quatern_d'] = 0
    # Please explain this
    img_nii.header['qoffset_x'] = -1 * (
        ((sub_headers[0]['X_DIMENSION'] * sub_headers[0]['X_PIXEL_SIZE'] * 10 / 2) - sub_headers[0][
            'X_PIXEL_SIZE'] * 5))
    img_nii.header['qoffset_y'] = -1 * (
        ((sub_headers[0]['Y_DIMENSION'] * sub_headers[0]['Y_PIXEL_SIZE'] * 10 / 2) - sub_headers[0][
            'Y_PIXEL_SIZE'] * 5))
    img_nii.header['qoffset_Z'] = -1 * (
        ((sub_headers[0]['Z_DIMENSION'] * sub_headers[0]['Z_PIXEL_SIZE'] * 10 / 2) - sub_headers[0][
            'Z_PIXEL_SIZE'] * 5))
    img_nii.header['srow_x'] = numpy.array([sub_headers[0]['X_PIXEL_SIZE']*10, 0, 0, img_nii.header['qoffset_x']])
    img_nii.header['srow_y'] = numpy.array([0, sub_headers[0]['Y_PIXEL_SIZE']*10, 0, img_nii.header['qoffset_y']])
    img_nii.header['srow_z'] = numpy.array([0, 0, sub_headers[0]['Z_PIXEL_SIZE']*10, img_nii.header['qoffset_z']])


    # img_nii.set_qform()
    # img_nii.set_sform()
    # img_nii.set_slice_durition()
    # img_nii.set_slice_times()
    # img_nii.set_slope_inter()
    # img.set_xyzt_units()
    # img.single_magic()
    # img._single_vox_offset()

    # nifti header items to include
    img_nii.header.set_xyzt_units('mm', 'unknown')

    # save nifti
    nibabel.save(img_nii, nifti_file)

    # used for testing veracity of nibabel read and write.
    if save_binary:
        pickle.dump(img_nii, open(nifti_file + '.pickle', "wb"))

    # write out timing file
    if sif_out:
        pass

    return img_nii
