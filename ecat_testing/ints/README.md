# matlab_numpy_ints

This is a very simple example of testing matlab vs python reading and writing of ecat files scaling up to a more
complex set of testing that reads real ecat data and writes it to niftis.

## Dead Simple Testing / Proofing 

Then simplest test cases that use "imaging" data made of small 2 x 1 arrays of integer data can found in:

`ints.m` and `ints.py`

## Outline of Testing on Real Data (e.g. steps required to read and write ecat into Nifti)

A part of this debugging process is to capture the state of inputs and outputs through each iteration of the python
and matlab code. These outputs are cataloged and saved in this directory (`ecat_testing/ints/`) within subdirectory 
`steps/`. The naming, order, and description of each step are laid out in the table below for easy reference. At each
of these steps the outputs are saved in the `steps/` directory with the filestem (and the python or matlab code used to 
make them) as described. These temporary files are written if and only if the environment variable `ECAT_SAVE_STEPS=1` 
is set.

| Step | Description                                           | Matlab        | Python         | FileStem                     |
|------|-------------------------------------------------------|---------------|----------------|------------------------------|
| 1    | Read main header                                      | `read_ECAT7.m` | `read_ecat.py` | `1_read_mh_ecat*`            |
| 2    | Read subheaders                                       | `read_EACT7.m` | `read_ecat.py` | `2_read_sh_ecat*`            |
| 3    | Determine file/data type                              | `read_ECAT7.m` | `read_ecat.py` | `3_determine_data_type*`     |
| 4    | Read image data                                       | `read_ECAT7.m` | `read_ecat.py` | `4_read_img_ecat*`           |
| 5    | scale if calibrated                                   | `read_ECAT7.m` | `read_ecat.py` | `5_scale_img_ecat*`          |
| 6    | Pass Data to ecat2nii                                 | `ecat2nii.m`  | `ecat2nii.py`  | `6_ecat2nii*`                |
| 7    | Flip ECAT data into Nifti space                       | `ecat2nii.m`  | `ecat2nii.py`  | `7_flip_ecat2nii*`           |
| 8    | Rescale to 16 bits                                    | `ecat2nii.m`  | `ecat2nii.py`  | `8_rescale_to_16_ecat2nii*`  |
| 9    | Calibration Units Scaling                             | `ecat2nii.m`  | `ecat2nii.py`  | `9_scal_cal_units_ecat2nii*` |
| 10   | Save to Nifti                                         | `ecat2nii.m`  | `ecat2nii.py`  | `10_save_nii_ecat2nii*`      |
| 11   | Check to see if values are recorded as they should be | `ecat2nii.m`   | `ecat2nii.py`   | `11_read_saved_nii*`          |


1. Read main header: this is the first step in reading the ecat file, the main header contains information about the
   file, the subheaders, and the image data. These will be saved as jsons for comparison.
2. Read subheaders: the subheaders contain information about the image data, these will be saved as jsons for comparison
   as well.
3. Determine file/data type: this step is to determine the type of data in the image data, this will be saved a json or 
   a text file with a single line specifying the datatype and endianness, but probably a json.
4. Read image data: this is the final step in reading the ecat file, the image data is read in and will be examined at 
   3 different time points (if available). E.g. the first frame, the middle frame, and the final frame. Only a single 2D
   slice will be saved from each of the time points, and it too will be taken from the "middle" of its 3D volume. We're
   only attempting to compare whether python and matlab have done a decent job of reading the data as recorded in.
5. Repeat step 4 but scale the data if it should be scaled
6. Save objects for comparison (as best as one can) before they are passed to the ecat2nii function. This will include
   the mainheader, subheaders, and image data.
7. Return the transformed data to the nifti space from ecat. This follows the 3 flip dimension steps performed across 
   the 3D image data. This output will use the same frames as step 4 and 5.
8. Rescale the data to 16 bits: this should only occur if the data is 12bit as is sometimes the case with ecat data. As 
   a note to self, attempting these steps in Python will start to lead to wildly different values when compared to 
   matlab. It's most likely not necessary to do this step as the data is handled in numpy, but this writer won't promise
   to eat his hat if it turns out to be necessary.
9. Calibration Units: (Search for 'calibration_units == 1' to locate this in code) Here we can potentially alter the 
   data again by scaling, rounding, and converting from int to float. As in steps 4 and 5 we will save the first, 
   middle, and last frames of the data as 2D slices in the middle of their respective 3D volumes for comparison.
10. Save to nifti: the data is saved to a nifti file and the output is saved for comparison as .nii files named in line
   with the FileStem column above.
11. Additional Steps: TBD
