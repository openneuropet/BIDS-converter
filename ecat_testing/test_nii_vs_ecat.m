[mh,sh,data] = readECAT7; % read in p9816fvat1_osem.ecat
nii = MRIread('p9816fvat1_osem.nii');

figure; imagesc(rot90(fliplr(squeeze(data{10}(:,:,40)))))
figure; imagesc(squeeze(nii.vol(:,:,40,10)))

ecat = rot90(fliplr(squeeze(data{10}(:,:,40))));
turku = squeeze(nii.vol(:,:,40,10));

val_ecat = ecat(10,6);
val_turku = turku(10,6);

scale_factor = sh{10}.scale_factor;
calibration_factor = mh.ecat_calibration_factor;

cf = scale_factor*calibration_factor;

print(val_ecatcf,val_turku)

vinci = [12055.6,50513.8,22912.1];
figure; plot(turku(24:26,65),vinci,'.')
mdl = fitlm(vinci,turku(24:26,65));