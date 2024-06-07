import nibabel
import pathlib
import numpy

steps_dir = pathlib.Path(__file__).parent / 'steps'

def first_middle_last_frames_to_text(four_d_array_like_object, output_folder, step_name='_step_name_'):
    frames = [0, four_d_array_like_object.shape[-1] // 2, four_d_array_like_object.shape[-1] - 1]
    frames_to_record = []
    for f in frames:
        frames_to_record.append(four_d_array_like_object[:, :, :, f])

    # now collect a single 2d slice from the "middle" of the 3d frames in frames_to_record
    for index, frame in enumerate(frames_to_record):
        numpy.savetxt(output_folder / f"{step_name}_frame_{frames[index]}.tsv",
                      frames_to_record[index][:, :, frames_to_record[index].shape[2] // 2],
                      delimiter="\t", fmt='%s')

path_to_matlab_nii = pathlib.Path('matlab_nii.nii')
path_to_python_nii = pathlib.Path('python_nii.nii.gz')


python_nii = nibabel.load(path_to_python_nii)
matlab_nii = nibabel.load(path_to_matlab_nii)

python_data = python_nii.get_fdata()
matlab_data = matlab_nii.get_fdata()

# compare the two arrays in each
print(numpy.allclose(python_data, matlab_data, rtol=0.01))


# subtract the two arrays
diff = python_data - matlab_data
print(f"difference max and min: {diff.max()}, {diff.min()}")
print(f"mean difference: {np.sqrt(np.mean(diff ** 2))}")

# save diff as nii
diff_nii = python_nii.__class__(diff, python_nii.affine, python_nii.header)
nibabel.save(diff_nii, steps_dir / '12_diff_between_written_niis.nii.gz')

first_middle_last_frames_to_text(diff, steps_dir, step_name='13_diff_between_written_niis')