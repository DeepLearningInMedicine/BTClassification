import os
import scipy.misc
import numpy as np
from tqdm import *
import nibabel as nib
import matplotlib.pyplot as plt
from scipy.ndimage.interpolation import zoom


def create_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def load_nii(path):
    return nib.load(path).get_data()


def plot_slices(slices):
    slice_num = len(slices)
    plt.figure()
    for i in range(slice_num):
        plt.subplot(1, slice_num, i + 1)
        plt.imshow(slices[i], cmap="gray")
        plt.axis("off")
    plt.show()


def trim(volume):
    none_zero_idx = np.where(volume > 0)

    min_i, max_i = np.min(none_zero_idx[0]), np.max(none_zero_idx[0])
    min_j, max_j = np.min(none_zero_idx[1]), np.max(none_zero_idx[1])

    diff_i = max_i - min_i
    diff_j = max_j - min_j

    if diff_i > diff_j:
        diff = diff_i - diff_j
        half_diff = diff // 2
        min_j -= half_diff
        max_j += (diff - half_diff)
    elif diff_i < diff_j:
        diff = diff_j - diff_i
        half_diff = diff // 2
        min_i -= half_diff
        max_i += (diff - half_diff)

    return min_i, max_i, min_j, max_j


def rescale(in_slice, target_shape=[224, 224]):
    factors = [t / s for s, t in zip(in_slice.shape, target_shape)]
    resized = zoom(in_slice, zoom=factors, order=1, prefilter=False)
    return resized


def norm(in_slice):
    return (in_slice - np.mean(in_slice)) / np.std(in_slice)


def save_to_dir(slices, mode, out_subj_dir):
    for i in range(len(slices)):
        type_dir = os.path.join(out_subj_dir, mode)
        create_dir(type_dir)
        in_slice = slices[i]
        in_slice_path = os.path.join(type_dir, str(i) + ".npy")
        in_slice_png_path = os.path.join(type_dir, str(i) + ".png")
        np.save(in_slice_path, in_slice)
        scipy.misc.imsave(in_slice_png_path, in_slice)
    return


parent_dir = os.path.dirname(os.getcwd())
input_dir = os.path.join(parent_dir, "VolumeData", "TCGA")
output_dir = os.path.join(parent_dir, "SliceData", "Brain")
subjects = os.listdir(input_dir)

print("Mark tumor in brain ...")
for subject in tqdm(subjects):
    in_subj_dir = os.path.join(input_dir, subject)
    out_subj_dir = os.path.join(output_dir, subject)
    create_dir(out_subj_dir)

    mask_path = os.path.join(in_subj_dir, subject + "_mask.nii.gz")
    t1ce_path = os.path.join(in_subj_dir, subject + "_t1Gd.nii.gz")
    t2_path = os.path.join(in_subj_dir, subject + "_t2.nii.gz")

    mask = load_nii(mask_path)
    t1Gd = load_nii(t1ce_path)
    t2 = load_nii(t2_path)

    min_i, max_i, min_j, max_j = trim(t1Gd)
    t1Gd = t1Gd[min_i:max_i, min_j:max_j, :]
    t2 = t2[min_i:max_i, min_j:max_j, :]
    mask = mask[min_i:max_i, min_j:max_j, :].astype(np.float32)

    tumor_mask_idx = []
    for i in range(mask.shape[2]):
        if np.sum(mask[..., i]) > 0:
            tumor_mask_idx.append(i)

    idx_len = len(tumor_mask_idx)
    mid_idx = idx_len // 2
    dif_idx = int(idx_len * 0.2)

    extract_idx = [tumor_mask_idx[mid_idx - dif_idx],
                   tumor_mask_idx[mid_idx],
                   tumor_mask_idx[mid_idx + dif_idx]]

    mask[np.where(mask > 0)] = 1
    mask[np.where(mask == 0)] = 0.333
    t1Gd = np.multiply(t1Gd, mask)
    t2 = np.multiply(t2, mask)

    t1Gd_slices = [norm(rescale(np.rot90(t1Gd[..., idx], 3))) for idx in extract_idx]
    t2_slices = [norm(rescale(np.rot90(t2[..., idx], 3))) for idx in extract_idx]

    save_to_dir(t1Gd_slices, "t1ce", out_subj_dir)
    save_to_dir(t2_slices, "t2", out_subj_dir)
