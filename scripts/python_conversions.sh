#!/bin/bash
# anthony galassi - Sept 2022
# Note this script uses dcm2niix and ecatpet2bids to convert a series of phantoms in BIDS, all conversions take place at the command line 
# and can be performed after installing pypet2bids with pip via `pip install pypet2bids`. Additional BIDS fields that are required for BIDS
# but not present in the source data are provided as command line arguments following the --kwargs flag. For the sake of readability the
# command like arguments are spaced one per line with a \ character to follow. In practice one would most like enter additional arguments
# without newlines or a trailer \ eg:
# --kwargs TimeZero="12:12:12" ScanStart=0
# --kwargs accepts arguments passed to in in the form of JS or Python types: int, float, string, list/array. Where lists/arrays should be 
# wrapped in double quotes.

# set paths where the repo is
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
repo_path=$( cd "$(dirname "${parent_path}")" ; pwd -P )

DESTINATION=$repo_path/python
SOURCE_FOLDER=$repo_path/sourcedata

echo "SOURCE_FOLDER ${SOURCE_FOLDER}, DESTINATION ${DESTINATION}"

mkdir $DESTINATION
cp $repo_path/dataset_description.json $DESTINATION/dataset_description.json

## Neurobiology Research Unit - Copenhagen
## ----------------------------------------
#
## Siemens HRRT
## ------------
#echo "${SOURCE_FOLDER}/SiemensHRRT-NRU/XCal-Hrrt-2022.04.21.15.43.05_EM_3D.v"
#ecatpet2bids $SOURCE_FOLDER/SiemensHRRT-NRU/XCal-Hrrt-2022.04.21.15.43.05_EM_3D.v --nifti $DESTINATION/sub-SiemensHRRTNRU/pet/sub-SiemensHRRTNRU_pet.nii --convert --kwargs \
#Manufacturer=Siemens \
#ManufacturersModelName=HRRT \
#InstitutionName="Rigshospitalet, NRU, DK" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName=FDG \
#TracerRadionuclide=F18 \
#InjectedRadioactivity=81.24 \
#SpecificRadioactivity="1.3019e+04" \
#ModeOfAdministration=infusion \
#AcquisitionMode="list mode" \
#ImageDecayCorrected="true" \
#ImageDecayCorrectionTime=0 \
#ReconFilterSize=0 \
#AttenuationCorrection="10-min transmission scan" \
#SpecificRadioactivityUnits="Bq" \
#ScanStart=0 \
#InjectionStart=0 \
#InjectedRadioactivityUnits='Bq' \
#ReconFilterType="none"
#
## Siemens Biograph
## ---------------------------
#echo "${SOURCE_FOLDER}/SiemensBiographPETMR-NRU"
#dcm2niix4pet $SOURCE_FOLDER/SiemensBiographPETMR-NRU --destination-path $DESTINATION/sub-SiemensBiographNRU/pet --kwargs \
#Manufacturer=Siemens \
#ManufacturersModelName=Biograph \
#InstitutionName="Rigshospitalet, NRU, DK" \
#BodyPart=Phantom \
#Units="Bq/mL" \
#TracerName="FDG" \
#TracerRadionuclide="F18" \
#InjectedRadioactivity=81.24 \
#SpecificRadioactivity=1.3019e+04 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#FrameTimesStart="[0]" \
#FrameDuration=[300] \
#ImageDecayCorrected="true" \
#ImageDecayCorrectionTime=0 \
#DecayCorrectionFactor=[1] \
#AttenuationCorrection="MR-corrected" \
#InjectionStart=0
#
## Århus University Hospital
## ---------------------------
#echo "${SOURCE_FOLDER}/GeneralElectricDiscoveryPETCT-Aarhus"
#dcm2niix4pet $SOURCE_FOLDER/GeneralElectricDiscoveryPETCT-Aarhus  --destination-path $DESTINATION/sub-GeneralElectricDiscoveryAarhus/pet --kwargs \
#Manufacturer="General Electric" \
#ManufacturersModelName="Discovery" \
#InstitutionName="Århus University Hospital, DK" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="FDG" \
#TracerRadionuclide="F18" \
#InjectedRadioactivity=25.5 \
#SpecificRadioactivity=4.5213e+03 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected=True \
#ImageDecayCorrectionTime=0 \
#AttenuationCorrection="MR-corrected" \
#FrameDuration=[1200] \
#ReconFilterSize=0 \
#ReconFilterType='none' \
#FrameTimesStart=[0] \
#ReconMethodParameterLabels="[none]" \
#ReconMethodParameterUnits="[none]" \
#ReconMethodParameterValues="[0]"
#
#echo "${SOURCE_FOLDER}/GeneralElectricSignaPETMR-Aarhus"
#dcm2niix4pet $SOURCE_FOLDER/GeneralElectricSignaPETMR-Aarhus --destination-path $DESTINATION/sub-GeneralElectricSignaAarhus/pet \
#--kwargs \
#Manufacturer="General Electric" \
#ManufacturersModelName="Signa PETMR" \
#InstitutionName="Århus University Hospital, DK" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="FDG" \
#TracerRadionuclide="F18" \
#InjectedRadioactivity=21 \
#SpecificRadioactivity=3.7234e+03 \
#ModeOfAdministration="infusion" \
#FrameDuration=[600] \
#FrameTimesStart=[0] \
#AcquisitionMode="list mode" \
#ImageDecayCorrected="true" \
#ImageDecayCorrectionTime=0 \
#AttenuationCorrection="MR-corrected" \
#ReconFilterType='unknown' \
#ReconFilterSize=1 \
#ReconMethodParameterLabels="[none, none]" \
#ReconMethodParameterUnits="[none, none]" \
#ReconMethodParameterValues="[0, 0]"
#
## Johannes Gutenberg University of Mainz
## --------------------------------------
#
## PhilipsGeminiPETMR
## --------------------------------------
#
#echo "${SOURCE_FOLDER}/PhilipsGeminiPETMR-Unimedizin/reqCTAC"
#dcm2niix4pet $SOURCE_FOLDER/PhilipsGeminiPETMR-Unimedizin/reqCTAC --destination-path $DESTINATION/sub-PhilipsGeminiUnimedizinMainz/pet \
#--kwargs \
#Manufacturer="Philips Medical Systems" \
#ManufacturersModelName="PET/CT Gemini TF16" \
#InstitutionName="Unimedizin, Mainz, DE" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="Fallypride" \
#TracerRadionuclide="F18" \
#InjectedRadioactivity=114 \
#SpecificRadioactivity=800 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected=True \
#ImageDecayCorrectionTime=0 \
#ReconFilterType='n/a' \
#ReconFilterSize=0 \
#AttenuationCorrection="CTAC-SG" \
#ScatterCorrectionMethod="SS-SIMUL" \
#ReconstructionMethod="LOR-RAMLA" \
#ReconMethodParameterValues="[1,1]" \
#FrameDuration=[1798] \
#ReconMethodParameterLabels="[none, none]" \
#ReconMethodParameterUnits="[none, none]" \
#FrameTimesStart=[0] \
#
#echo "${SOURCE_FOLDER}/PhilipsGeminiPETMR-Unimedizin/reqNAC"
#dcm2niix4pet $SOURCE_FOLDER/PhilipsGeminiPETMR-Unimedizin/reqNAC --destination-path $DESTINATION/sub-PhilipsGeminiNACUnimedizinMainz/pet \
#--kwargs \
#Manufacturer="Philips Medical Systems" \
#ManufacturersModelName="PET/CT Gemini TF16" \
#InstitutionName="Unimedizin, Mainz, DE" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="Fallypride" \
#TracerRadionuclide="F18" \
#InjectedRadioactivity=114 \
#SpecificRadioactivity=800 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected=True \
#ImageDecayCorrectionTime=0 \
#ReconFilterType=None \
#ReconFilterSize=0 \
#AttenuationCorrection="None" \
#ScatterCorrectionMethod="None" \
#ReconstructionMethod="3D-RAMLA" \
#FrameDuration=[1798] \
#ReconMethodParameterLabels="[none, none]" \
#ReconMethodParameterUnits="[none, none]" \
#ReconMethodParameterValues="[1,1]" \
#FrameTimesStart=[0] \
#
#
## Amsterdam UMC
## ---------------------------
#
## Philips Ingenuity PET-CT
## -----------------------
#echo "${SOURCE_FOLDER}/PhilipsIngenuityPETCT-AmsterdamUMC"
#dcm2niix4pet $SOURCE_FOLDER/PhilipsIngenuityPETCT-AmsterdamUMC --destination-path $DESTINATION/sub-PhilipsIngenuityPETCTAmsterdamUMC/pet \
#--kwargs \
#Manufacturer="Philips Medical Systems" \
#ManufacturersModelName="Ingenuity TF PET/CT" \
#InstitutionName="AmsterdamUMC,VUmc" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="Butanol" \
#TracerRadionuclide="O15" \
#InjectedRadioactivity=185 \
#SpecificRadioactivity=1.9907e+04 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected="true" \
#ImageDecayCorrectionTime=0 \
#DecayCorrectionFactor=[1] \
#ReconFilterSize=0 \
#ReconMethodParameterValues=[1] \
#AttenuationCorrection="CTAC-SG" \
#RandomsCorrectionMethod="DLYD" \
#ScatterCorrectionMethod="SS-SIMUL" \
#ReconstructionMethod="BLOB-OS-TF" \
#ReconMethodParameterLabels="[none, none]" \
#ReconMethodParameterUnits="[none, none]" \
#ReconMethodParameterValues="[0, 0]" \
#ReconFilterType="none" \
#
## Philips Ingenuity PET-MRI
## -------------------------
#echo "${SOURCE_FOLDER}/PhilipsIngenuityPETMR-AmsterdamUMC"
#dcm2niix4pet $SOURCE_FOLDER/PhilipsIngenuityPETMR-AmsterdamUMC --destination-path $DESTINATION/sub-PhilipsIngenuityPETMRAmsterdamUMC/pet \
#--kwargs \
#Manufacturer="Philips Medical Systems" \
#ManufacturersModelName="Ingenuity TF PET/MR" \
#InstitutionName="AmsterdamUMC,VUmc" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="11C-PIB" \
#TracerRadionuclide="C11" \
#InjectedRadioactivity=135.1 \
#SpecificRadioactivity=1.4538e+04 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected="True" \
#ImageDecayCorrectionTime=0 \
#ReconFilterType="None" \
#ReconFilterSize=0 \
#AttenuationCorrection="MRAC" \
#RandomsCorrectionMethod="DLYD" \
#ScatterCorrectionMethod="SS-SIMUL" \
#ReconstructionMethod="LOR-RAMLA" \
#ReconMethodParameterValues="[1, 1]" \
#ReconFilterType="['n/a', 'n/a']" \
#DecayCorrectionFactor=[1] \
#ReconMethodParameterLabels="[none, none]" \
#ReconMethodParameterUnits="[none, none]" \
#ReconMethodParameterValues="[0, 0]"
#
## philipsVereosPET-CT
## -------------------
#echo "${SOURCE_FOLDER}/PhilipsVereosPETCT-AmsterdamUMC"
#dcm2niix4pet $SOURCE_FOLDER/PhillipsVereosPETCT-AmsterdamUMC --destination-path $DESTINATION/sub-PhillipsVereosAmsterdamUMC/pet \
#--kwargs \
#Manufacturer="Philips Medical Systems" \
#ManufacturersModelName="Vereos PET/CT" \
#InstitutionName="AmsterdamUMC,VUmc" \
#BodyPart="Phantom" \
#Units="Bq/mL" \
#TracerName="11C-PIB" \
#TracerRadionuclide="C11" \
#InjectedRadioactivity=202.5 \
#SpecificRadioactivity=2.1791e+04 \
#ModeOfAdministration="infusion" \
#AcquisitionMode="list mode" \
#ImageDecayCorrected="True" \
#ImageDecayCorrectionTime=0 \
#ReconFilterType="None" \
#ReconFilterSize=0 \
#AttenuationCorrection="CTAC-SG" \
#ScatterCorrectionMethod="SS-SIMUL" \
#RandomsCorrectionMethod="DLYD" \
#ReconstructionMethod="OSEMi3s15" \
#TimeZero="11:40:24"

# National Institute of Mental Health, Bethesda
# ----------------------------------------------

# Siemens Biograph - AC_TOF 
# --------------------------
echo "${SOURCE_FOLDER}/SiemensBiographPETMR-NIMH/AC_TOF"
dcm2niix4pet $SOURCE_FOLDER/SiemensBiographPETMR-NIMH/AC_TOF --destination-path $DESTINATION/sub-SiemensBiographNIMH/pet \
--kwargs \
Manufacturer="Siemens" \
ManufacturersModelName="Biograph - petmct2" \
InstitutionName="NIH Clinical Center, USA" \
BodyPart="Phantom" \
Units="Bq/mL" \
TracerName="FDG" \
TracerRadionuclide="F18" \
InjectedRadioactivity=44.4 \
SpecificRadioactivity=7.1154e+03 \
ModeOfAdministration="infusion" \
AcquisitionMode="list mode" \
ImageDecayCorrected="True" \
ImageDecayCorrectionTime=0 \
FrameTimesStart=[0] \
FrameDuration=[300] \
AttenuationCorrection="MR-corrected" \
RandomsCorrectionMethod="DLYD" \
ReconFilterSize=1 \
--silent
#DecayCorrectionFactor="[1]" \

# General Electric Medical Systems Signa PET-MR
# ----------------------------------------------
echo "${SOURCE_FOLDER}/GeneralElectricSignaPETMR-NIMH"
FrameTimesStart=0
dcm2niix4pet $SOURCE_FOLDER/GeneralElectricSignaPETMR-NIMH --destination-path $DESTINATION/sub-GeneralElectricSignaNIMH/pet \
--kwargs \
TimeZero="14:08:45" \
Manufacturer="GE MEDICAL SYSTEMS" \
ManufacturersModelName="SIGNA PET/MR" \
InstitutionName="NIH Clinical Center, USA" \
BodyPart="Phantom" \
Units="Bq/mL" \
TracerName="Gallium citrate" \
TracerRadionuclide="Germanium68" \
InjectedRadioactivity=1 \
SpecificRadioactivity=23423.75 \
ModeOfAdministration="infusion" \
FrameTimesStart=0 \
AcquisitionMode="list mode" \
ImageDecayCorrected="False" \
FrameTimesStart="[0]" \
ImageDecayCorrectionTime=0 \
ReconFilterType="n/a" \
ReconFilterSize=1 \
ReconMethodParameterLabels="[none, none]" \
ReconMethodParameterUnits="[none, none]" \
ReconMethodParameterValues="[0, 0]" \
--silent


# General Electric Medical Systems Advance
# -----------------------------------------
echo "${SOURCE_FOLDER}/GeneralElectricAdvance-NIMH"
dcm2niix4pet $SOURCE_FOLDER/GeneralElectricAdvance-NIMH/2d_unif_lt_ramp --destination-path $DESTINATION/sub-GeneralElectricAdvanceNIMH/pet --kwargs \
Manufacturer="GE MEDICAL SYSTEMS" \
ManufacturersModelName="GE Advance" \
InstitutionName="NIH Clinical Center, USA" \
BodyPart="Phantom" \
Units="Bq/mL" \
TracerName="FDG" \
TracerRadionuclide="F18" \
InjectedRadioactivity=75.8500 \
InjectionStart=0 \
SpecificRadioactivity=418713.8 \
ModeOfAdministration="infusion" \
FrameTimesStart="[0]" \
ImageDecayCorrected='true' \
AcquisitionMode='list mode' \
ImageDecayCorrectionTime="0" \
ScatterCorrectionMethod="Convolution subtraction" \
FrameDuration="[98000]" \
ScanStart="0" \
ReconMethodParameterLabels="[none]" \
ReconMethodParameterUnits="[none]" \
ReconMethodParameterValues="[0, 0]" \
--silent
#TimeZero="13:39:41" \
#AttenuationCorrection='n/a' \


echo "${SOURCE_FOLDER}/GeneralElectricAdvance-NIMH"
dcm2niix4pet $SOURCE_FOLDER/GeneralElectricAdvance-NIMH/long_trans --destination-path $DESTINATION/sub-GeneralElectricAdvanceLongNIMH/pet --kwargs \
Manufacturer="GE MEDICAL SYSTEMS" \
ManufacturersModelName="GE Advance" \
InstitutionName="NIH Clinical Center, USA" \
BodyPart="Phantom" \
Units="Bq/mL" \
TracerName="FDG" \
TracerRadionuclide="F18" \
InjectedRadioactivity=75.8500 \
InjectionStart=0 \
SpecificRadioactivity=418713.8 \
ModeOfAdministration="infusion" \
FrameTimesStart="[0]" \
ImageDecayCorrected='false' \
AttenuationCorrection='measured' \
AcquisitionMode='list mode' \
ImageDecayCorrectionTime="0" \
FrameDuration="[98000]" \
ScatterCorrectionMethod="Gaussian Fit" \
ScanStart="0" \
ReconMethodParameterLabels="[none, none]" \
ReconMethodParameterUnits="[none, none]" \
ReconMethodParameterValues="[0, 0]" \
--silent

# Johns Hopkins University
# ------------------------

# Siemens HRRT
# ------------
echo "${SOURCE_FOLDER}/SiemensHRRT-JHU"
ecatpet2bids $SOURCE_FOLDER/SiemensHRRT-JHU/Hoffman.v \
--nifti $DESTINATION/sub-SiemensHRRTJHU/pet/sub-SiemensHRRTJHU_pet.nii.gz \
--convert \
--kwargs \
Manufacturer='Siemens' \
ManufacturersModelName='HRRT' \
InstitutionName='Johns Hopkins University, USA' \
BodyPart='Phantom' \
Units='Bq/mL' \
TracerName='FDG' \
TracerRadionuclide='F18' \
InjectedRadioactivity=0.788 \
InjectedRadioactivityUnits='mCi' \
SpecificRadioactivity='n/a' \
SpecificRadioactivityUnits='n/a' \
ModeOfAdministration='infusion' \
AcquisitionMode='list mode' \
ImageDecayCorrected=true \
ImageDecayCorrectionTime=0 \
AttenuationCorrection='transmission scan with a 137Cs point source' \
ScatterCorrectionMethod='Single-scatter simulation' \
ScanStart=0 \
InjectionStart=-2183 \
ReconMethodParameterLabels='["subsets", "iterations"]' \
ReconMethodParameterUnits='["none", "none"]' \
ReconMethodParameterValues='[16, 2]' \
ReconFilterType='Gaussian' \
ReconFilterSize=2

# General Electric Medical Systems Advance
# -----------------------------------------
dcm2niix4pet $SOURCE_FOLDER/GeneralElectricAdvance-JHU/ --destination-path $DESTINATION/sub-GeneralElectricAdvanceJHU/pet --kwargs \
Manufacturer='GE MEDICAL SYSTEMS' \
ManufacturersModelName='GE Advance' \
InstitutionName='Johns Hopkins University, USA' \
BodyPart='Phantom' \
Units='Bq/mL' \
TracerName='FDG' \
TracerRadionuclide='F18' \
InjectedRadioactivity=0.788 \
InjectedRadioactivityUnits='mCi' \
SpecificRadioactivity='n/a' \
SpecificRadioactivityUnits='n/a' \
ModeOfAdministration='infusion' \
ScanStart=0 \
InjectionStart=-5336 \
FrameTimesStart="[0]" \
AcquisitionMode='list mode' \
ImageDecayCorrected='true' \
ImageDecayCorrectionTime=0 \
ScatterCorrectionMethod='Single-scatter simulation' \
ReconMethodParameterLabels='["none"]' \
ReconMethodParameterUnits='["none"]' \
ReconMethodParameterValues='[0]' \
ReconFilterType="none" \
ReconFilterSize=0 \
AttenuationCorrection='2D-acquired transmission scan with a 68Ge pin'



# Chesapeake Medical Imaging
# --------------------------


# Canon Cartesion Prime PET-CT
# ----------------------------
dcm2niix4pet $SOURCE_FOLDER/CanonCartesionPrimePETCT-NIA --destination-path $DESTINATION/sub-CanonCartesionPrimeNIA/pet --kwargs \
Manufacturer='Canon Medical Systems' \
ManufacturersModelName='Cartesion Prime' \
InstitutionName='Chesapeake Medical Imaging, USA' \
BodyPart='Phantom' \
Units='Bq/mL' \
TracerName='FDG' \
TracerRadionuclide='F18' \
InjectedRadioactivity=0.87 \
InjectedRadioactivityUnits='mCi' \
SpecificRadioactivity='n/a' \
SpecificRadioactivityUnits='n/a' \
ModeOfAdministration='infusion' \
ScanStart=0 \
InjectionStart=-2312 \
FrameTimesStart="[0, 300, 600, 900]" \
AcquisitionMode='list mode' \
ImageDecayCorrected='true' \
ImageDecayCorrectionTime=0 \
ReconMethodParameterValues="[24, 5]" \
ReconMethodParameterUnits="['none', 'none']" \
ReconMethodParameterLabels="['subsets', 'iterations']" \
ReconFilterType="Gaussian" \
ReconFilterSize=4

