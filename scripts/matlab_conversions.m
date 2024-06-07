% this is how source data were converted using matlab
% note that usually we use the *parameter.txt file facilitating the metadata
% information but here it is done fully for completeness
% 
% cyril pernet - Nov 2023

%% set paths where the repo is to bypass the path/env parts below
% source      = 'D:\BIDS\ONP\OpenNeuroPET-Phantoms\sourcedata\';
% destination = 'D:\BIDS\ONP\OpenNeuroPET-Phantoms\';

%% get the path to this script
matlab_conversions_script_path = mfilename('fullpath');

%% get the path to the parent folder
parts                = strsplit(matlab_conversions_script_path, filesep);
code_folder_path     = strjoin(parts(1:end-1), filesep);
phantoms_folder_path = strjoin(parts(1:end-2),filesep);

%% set source and destination paths relative to this script/phantom folder
source      = strjoin({phantoms_folder_path, 'sourcedata'}, filesep);
destination = strjoin({phantoms_folder_path, 'matlab'}, filesep);

if ~exist(destination,'dir')
    mkdir(destination)
end
copyfile(strjoin({phantoms_folder_path, 'dataset_description.json'}, filesep), strjoin({destination, 'dataset_description.json'}, filesep))

%% sets the environment variable so that matlab can reach dcm2niix on posix
if ismac
    setenv('PATH', [getenv('PATH') ':/opt/homebrew/bin' ]);
    [status, results] = system('which dcm2niix');
    if status == 0
       dcm2niix_path = results;
        system([dcm2niix_path, ' -h'])
    else
        print_me = ['This script expects to find dcm2niix at /opt/homebrew/bin, for a default brew installed dcm2niix.'];
        disp(print_me)
    end
elseif ismac && ismac == 0
    [status, results] = system('which dcm2niix');
    if status == 0
        temp_str = strjoin({':', strtrim(results)}, '');
        setenv('PATH', [getenv('PATH') temp_str]);
    else
        print_me = ['Unable to determine path of dcm2niix on this unix machine, is dcm2niix installed?'];
        disp(print_me)
    end
else
    disp("Good luck running this on your non-unix computer.")
end

message = 'Failed to convert subject, moving onto next.';


%%% Neurobiology Research Unit - Copenhagen
%% ----------------------------------------
%
%% Siemens HRRT
%% ------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Siemens';
%    meta.ManufacturersModelName     = 'HRRT';
%    meta.InstitutionName            = 'Rigshospitalet, NRU, DK';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'FDG';
%    meta.TracerRadionuclide         = 'F18';
%    meta.InjectedRadioactivity      = 81.24; % Mbq
%    meta.SpecificRadioactivity      = 1.3019e+04; % ~ 81240000 Bq/ 6240 g
%    meta.ModeOfAdministration       = 'infusion';
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = true; % when passing this as string it fails validation
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.ReconFilterType            = 'none';
%    meta.ReconFilterSize            = 0;
%    meta.AttenuationCorrection      = '10-min transmission scan';
%    % meta.FrameDuration            = 1200; % not needed, encoded in ecat even for 4D images
%    % meta.FrameTimesStart          = 0;
%
%    out = ecat2nii(fullfile(source,['SiemensHRRT-NRU' filesep 'XCal-Hrrt-2022.04.21.15.43.05_EM_3D.v']),...
%        meta,'gz',true,'FileListOut',fullfile(destination,['sub-SiemensHRRTNRU'  filesep 'pet' filesep 'sub-SiemensHRRTNRU.nii']));
%
%catch
%    disp(message);
%end
%
%% Siemens Biograph
%% ---------------------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Siemens';
%    meta.ManufacturersModelName     = 'Biograph';
%    meta.InstitutionName            = 'Rigshospitalet, NRU, DK';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'FDG';
%    meta.TracerRadionuclide         = 'F18';
%    meta.InjectedRadioactivity      = 81.24; % Mbq
%    meta.SpecificRadioactivity      = 1.3019e+04; % ~ 81240000 Bq/ 6240 g
%    meta.ModeOfAdministration       = 'infusion';
%    meta.FrameTimesStart            = 0;
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'MR-corrected';
%    meta.FrameDuration              = 300;
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "none";
%    meta.ReconFilterSize            = 1;
%
%    dcm2niix4pet(fullfile(source,'SiemensBiographPETMR-NRU'),meta,...
%        'o',fullfile(destination,['sub-SiemensBiographNRU' filesep 'pet'])); % note we only need to use folders here
%catch
%    disp(message);
%end
%
%%% Århus University Hospital
%% ---------------------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'General Electric';
%    meta.ManufacturersModelName     = 'Discovery';
%    meta.InstitutionName            = 'Århus University Hospital, DK';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'FDG';
%    meta.TracerRadionuclide         = 'F18';
%    meta.InjectedRadioactivity      = 25.5; % Mbq
%    meta.SpecificRadioactivity      = 4.5213e+03; % ~ 25500000 / 5640 ml
%    meta.ModeOfAdministration       = 'infusion';
%    meta.FrameTimesStart            = 0;
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'MR-corrected';
%    meta.FrameDuration              = 1200;
%    meta.FrameTimesStart            = 0;
%    meta.ReconMethodParameterLabels = ["none"];
%    meta.ReconMethodParameterUnits  = ["none"];
%    meta.ReconParameterValues       = [0];
%    meta.ReconFilterType            = "none";
%    meta.ReconFilterSize            = 0;
%
%    dcm2niix4pet(fullfile(source,'GeneralElectricDiscoveryPETCT-Aarhus'),meta,...
%        'o',fullfile(destination,['sub-GeneralElectricDiscoveryAarhus' filesep 'pet'])); % note we only need to use folders here
%
%catch
%    disp(message);
%end
%
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'General Electric';
%    meta.ManufacturersModelName     = 'Signa PET/MR';
%    meta.InstitutionName            = 'Århus University Hospital, DK';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'FDG';
%    meta.TracerRadionuclide         = 'F18';
%    meta.InjectedRadioactivity      = 21; % Mbq
%    meta.SpecificRadioactivity      = 3.7234e+03; % ~ 21000000 Bq/ 5640 ml
%    meta.ModeOfAdministration       = 'infusion';
%    meta.FrameTimesStart            = 0;
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'MR-corrected';
%    meta.FrameDuration              = 600;
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "none";
%    meta.ReconFilterSize            = 0;
%    meta.ReconMethodParameterLabels = ["none"];
%    meta.ReconMethodParameterUnits  = ["none"];
%    meta.ReconMethodParameterValues = [0];
%    meta.InjectionEnd               = [10];
%
%    dcm2niix4pet(fullfile(source,'GeneralElectricSignaPETMR-Aarhus'),meta,...
%        'o',fullfile(destination,['sub-GeneralElectricSignaAarhus' filesep 'pet'])); % note we only need to use folders here
%
%catch
%    disp(message);
%end
%
%
%%% Johannes Gutenberg University of Mainz
%% --------------------------------------
%% this phillips misbehaves not running it
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Philips Medical Systems';
%    meta.ManufacturersModelName     = 'PET/CT Gemini TF16';
%    meta.InstitutionName            = 'Unimedizin, Mainz, DE';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'Fallypride';
%    meta.TracerRadionuclide         = 'F18';
%    meta.InjectedRadioactivity      = 114; % Mbq
%    meta.SpecificRadioactivity      = 800; %  ~ 114000000 Bq/ 142500 g
%    meta.ModeOfAdministration       = 'infusion'; %'Intravenous route'
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'CTAC-SG';
%    meta.ScatterCorrectionMethod    = 'SS-SIMUL';
%    meta.ReconstructionMethod       = 'LOR-RAMLA';
%    meta.FrameDuration              = 1798;
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "none";
%    meta.ReconFilterSize            = 1;
%
%    %dcm2niix4pet(fullfile(source,['PhilipsGeminiPETMR-Unimedizin' filesep 'reqCTAC']),meta,...
%    %    'o',fullfile(destination,['sub-PhilipsGeminiUnimedizinMainz' filesep 'pet']));
%
%
%    % meta.AttenuationCorrection      = 'NONE';
%    % meta.ScatterCorrectionMethod    = 'NONE';%GEG
%    % meta.ReconstructionMethod       = '3D-RAMLA';%GEG
%    % dcm2niix4pet(fullfile(source,['PhilipsGemini-Unimedizin' filesep 'reqNAC']),meta,...
%    %     'o',fullfile(destination,['sub-PhilipsGeminiNAC-UnimedizinMainz' filesep 'pet']));
%
%catch
%    disp(message);
%end
%
%%% Amsterdam UMC
%% ---------------------------
%
%% Philips Ingenuity PET-CT
%% -----------------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Philips Medical Systems';
%    meta.ManufacturersModelName     = 'Ingenuity TF PET/CT';
%    meta.InstitutionName            = 'AmsterdamUMC,VUmc';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = 'Butanol';
%    meta.TracerRadionuclide         = 'O15';
%    meta.InjectedRadioactivity      = 185; % Mbq
%    meta.SpecificRadioactivity      = 1.9907e+04; %  ~ 185000000 Bq/ 9293 ml
%    meta.ModeOfAdministration       = 'infusion'; %'Intravenous route'
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'CTAC-SG';
%    meta.RandomsCorrectionMethod    = 'DLYD'; % field added in our library
%    meta.ScatterCorrectionMethod    = 'SS-SIMUL';  % field added in our library
%    meta.ReconstructionMethod       = 'BLOB-OS-TF';
%    %meta.FrameDuration              = repmat(122.238007,20,1);
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "unknown";
%    meta.ReconFilterSize            = 1;
%
%    dcm2niix4pet(fullfile(source,'PhilipsIngenuityPETCT-AmsterdamUMC'),meta,...
%        'o',fullfile(destination,['sub-PhilipsIngenuityPETCTAmsterdamUMC' filesep 'pet']));
%catch
%    disp(message);
%end
%
%% Philips Ingenuity PET-MRI
%% -------------------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Philips Medical Systems';
%    meta.ManufacturersModelName     = 'Ingenuity TF PET/MR';
%    meta.InstitutionName            = 'AmsterdamUMC,VUmc';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = '11C-PIB';
%    meta.TracerRadionuclide         = 'C11';
%    meta.InjectedRadioactivity      = 135.1; % Mbq
%    meta.SpecificRadioactivity      = 1.4538e+04; %  ~ 135100000 Bq/ 9293 ml
%    meta.ModeOfAdministration       = 'infusion'; %'Intravenous route'
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.ReconFilterType            = 'none';
%    meta.ReconFilterSize            = 0;
%    meta.AttenuationCorrection      = 'MRAC';
%    meta.RandomsCorrectionMethod    = 'DLYD';
%    meta.ScatterCorrectionMethod    = 'SS-SIMUL';
%    meta.ReconstructionMethod       = 'LOR-RAMLA';
%    %meta.FrameDuration              = repmat(122.238007,40,1);
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "unknown";
%    meta.ReconFilterSize            = 1;
%
%    dcm2niix4pet(fullfile(source,'PhilipsIngenuityPETMR-AmsterdamUMC'),meta,...
%        'o',fullfile(destination,['sub-PhilipsIngenuityPETMRAmsterdamUMC' filesep 'pet']));
%catch
%    disp(message);
%end
%
%% PhillipsVereosPET-CT
%% -------------------
%try
%    clear meta
%    meta.TimeZero                   = 'ScanStart';
%    meta.Manufacturer               = 'Philips Medical Systems';
%    meta.ManufacturersModelName     = 'Vereos PET/CT';
%    meta.InstitutionName            = 'AmsterdamUMC,VUmc';
%    meta.BodyPart                   = 'Phantom';
%    meta.Units                      = 'Bq/mL';
%    meta.TracerName                 = '11C-PIB';
%    meta.TracerRadionuclide         = 'C11';
%    meta.InjectedRadioactivity      = 202.5; % Mbq
%    meta.SpecificRadioactivity      = 2.1791e+04; %  ~ 202500000 Bq/ 9293 ml
%    meta.ModeOfAdministration       = 'infusion'; %'Intravenous route'
%    meta.AcquisitionMode            = 'list mode';
%    meta.ImageDecayCorrected        = 'true';
%    meta.ImageDecayCorrectionTime   = 0;
%    meta.AttenuationCorrection      = 'CTAC-SG';
%    meta.ScatterCorrectionMethod    = 'SS-SIMUL';
%    meta.RandomsCorrectionMethod    = 'DLYD';
%    meta.ReconstructionMethod       = 'OSEM:i3s15';
%    %meta.FrameDuration              = repmat(1221.780029,40,1);
%    meta.FrameTimesStart            = 0;
%    meta.ReconFilterType            = "unknown";
%    meta.ReconFilterSize            = 1;
%
%    dcm2niix4pet(fullfile(source,'PhillipsVereosPETCT-AmsterdamUMC'),meta,...
%        'o',fullfile(destination,['sub-PhillipsVereosAmsterdamUMC' filesep 'pet']));
%catch
%    disp(message);
%end

%% National Institute of Mental Health, Bethesda
% ----------------------------------------------

% Siemens Biograph - AC_TOF 
% --------------------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'Siemens';
    meta.ManufacturersModelName     = 'Biograph - petmct2';
    meta.InstitutionName            = 'NIH Clinical Center, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 44.4; % Mbq
    meta.SpecificRadioactivity      = 7.1154e+03; % ~ 44400000 Bq/ 6240 g
    meta.ModeOfAdministration       = 'infusion';
    meta.FrameTimesStart            = 0;
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = 'true';
    meta.ImageDecayCorrectionTime   = 0;
    meta.AttenuationCorrection      = 'MR-corrected';
    meta.RandomsCorrectionMethod    = 'DLYD';
    meta.FrameDuration              = 300;
    meta.FrameTimesStart            = 0;
    meta.ReconFilterType            = "unknown";
    meta.ReconFilterSize            = 1;

    dcm2niix4pet(fullfile(source,['SiemensBiographPETMR-NIMH' filesep 'AC_TOF']),meta,...
         'o',fullfile(destination,['sub-SiemensBiographNIMH' filesep 'pet'])); 
catch
    disp(message);
end

% General Electric Medical Systems Signa PET-MR
% ----------------------------------------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'GE MEDICAL SYSTEMS';
    meta.ManufacturersModelName     = 'SIGNA PET/MR';
    meta.InstitutionName            = 'NIH Clinical Center, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'Gallium citrate';
    meta.TracerRadionuclide         = 'Germanium68';
    meta.InjectedRadioactivity      = 1; % Mbq
    meta.SpecificRadioactivity      = 23423.75; % ~ 44400000 Bq/ 6240 g
    meta.ModeOfAdministration       = 'infusion';
    meta.FrameTimesStart            = 0;
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = 'false';
    meta.ImageDecayCorrectionTime   = 0;
    meta.FrameDuration              = 98000;
    meta.FrameTimesStart            = 0;
    meta.ReconFilterType            = "none";
    meta.ReconFilterSize            = 1;

    dcm2niix4pet(fullfile(source,'GeneralElectricSignaPETMR-NIMH'),meta,...
        'o',fullfile(destination,['sub-GeneralElectricSignaNIMH' filesep 'pet'])); 
catch
    disp(message);
end

% General Electric Medical Systems Advance
% -----------------------------------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'GE MEDICAL SYSTEMS';
    meta.ManufacturersModelName     = 'GE Advance';
    meta.InstitutionName            = 'NIH Clinical Center, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 75.8500; % Mbq
    meta.SpecificRadioactivity      = 418713.8; % ~ 75850000 Bq/ 6240 g
    meta.ModeOfAdministration       = 'infusion';
    meta.FrameTimesStart            = 0;
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = 'true';
    meta.ImageDecayCorrectionTime   = 0;
    meta.ScatterCorrectionMethod    = 'Gaussian Fit';
    meta.FrameDuration              = 98000;
    meta.FrameTimesStart            = 0;
    meta.ReconMethodParameterLabels = ["none"];
    meta.ReconParameterUnits        = ["none"];
    meta.ReconMethodParameterValues = [0];
    meta.ReconFilterType            = "none";
    meta.ReconFilterSize            = 1;

    dcm2niix4pet(fullfile(source,['GeneralElectricAdvance-NIMH' filesep ...
        '2d_unif_lt_ramp']),meta,'o',fullfile(destination,['sub-GeneralElectricAdvanceNIMH' filesep 'pet'])); 
     
    % dcm2niix4pet(fullfile(source,['GeneralElectricAdvance-NIMH' filesep ...
    %     '3d_unif_lt_ramp']),meta,'o',fullfile(destination,['sub-GEAdvance3d-NIMH' filesep 'pet'])); 
    % 
    % dcm2niix4pet(fullfile(source,['GeneralElectricAdvance-NIMH' filesep ...
    %     '3d375_unif_lt_ramp']),meta,'o',fullfile(destination,['sub-GEAdvance3d375-NIMH' filesep 'pet'])); 
    % 
catch
    disp(message);
end

try
    meta.AttenuationCorrection = 'measured' ; % some how the field is not there
    meta.ReconMethodParameterLabels = ["none", "none"];
    meta.ReconMethodParameterUnits = ["none", "none"];
    meta.ReconMethodParameterValues = [0, 0];
    meta.FrameDuration = 98000;

    dcm2niix4pet(fullfile(source,['GeneralElectricAdvance-NIMH' filesep ...
        'long_trans']),meta,'o',fullfile(destination,['sub-GeneralElectricAdvanceLongNIMH' filesep 'pet']));
catch
    disp(message);
end

% Siemens HRRT
% ------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'Siemens';
    meta.ManufacturersModelName     = 'HRRT';
    meta.InstitutionName            = 'JHU';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 81.24; % Mbq
    meta.SpecificRadioactivity      = 1.3019e+04; % ~ 81240000 Bq/ 6240 g
    meta.ModeOfAdministration       = 'infusion';
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = true; % when passing this as string it fails validation
    meta.ImageDecayCorrectionTime   = 0;
    meta.ReconFilterType            = 'none';
    meta.ReconFilterSize            = 0;
    meta.AttenuationCorrection      = '10-min transmission scan';
    meta.ScatterFraction            = 0.0;
    meta.PromptRate                 = 0.0;
    meta.RandomsRate                = 0.0;
    meta.SinglesRate                = 0.0;

    out = ecat2nii(fullfile(source,['SiemensHRRT-JHU' filesep 'Hoffman.v']),...
        meta,'gz',true,'FileListOut',fullfile(destination,['sub-SiemensHRRTJHU'  filesep 'pet' filesep 'sub-SiemensHRRTJHU.nii']));


%% Johns Hopkins University
% ----------------------------------------------

% Siemens HRRT
% ------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'Siemens';
    meta.ManufacturersModelName     = 'HRRT';
    meta.InstitutionName            = 'Johns Hopkins University, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 0.788;
    meta.InjectedRadioactivityUnits = 'mCi';
    meta.SpecificRadioactivity      = 'n/a';
    meta.SpecificRadioactivityUnits = 'n/a';
    meta.ModeOfAdministration       = 'infusion';   
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = true; % when passing this as string it fails validation
    meta.ImageDecayCorrectionTime   = 0;
    meta.ReconFilterType            = 'Gaussian';
    meta.ReconFilterSize            = 2;
    meta.AttenuationCorrection      = 'transmission scan with a 137Cs point source';
    meta.ScatterCorrectionMethod    = 'Single-scatter simulation';
    meta.ScanStart                  = 0;
    meta.InjectionStart             = -2183;
    meta.ReconMethodParameterLabels = ["subsets" "iterations"];
    meta.ReconMethodParameterLabels = ["none" "none"];
    meta.ReconMethodParameterValues = [16 2];
    
    out = ecat2nii(fullfile(source,['SiemensHRRT-JHU' filesep 'Hoffman.v']),...
        meta,'gz',true,'FileListOut',fullfile(destination,['sub-SiemensHRRTJHU'  filesep 'pet' filesep 'sub-SiemensHRRTJHU.nii']));

catch
    disp(message);
end


% General Electric Medical Systems Advance
% -----------------------------------------
try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'GE MEDICAL SYSTEMS';
    meta.ManufacturersModelName     = 'GE Advance';
    meta.InstitutionName            = 'Johns Hopkins University, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 0.788;
    meta.InjectedRadioactivityUnits = 'mCi';
    meta.SpecificRadioactivity      = 'n/a';
    meta.SpecificRadioactivityUnits = 'n/a';
    meta.ModeOfAdministration       = 'infusion';
    meta.ScanStart                  = 0;
    meta.InjectionStart             = -5336;
    meta.FrameTimesStart            = 0;
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = 'true';
    meta.ImageDecayCorrectionTime   = 0;
    meta.ScatterCorrectionMethod    = 'Single-scatter simulation';
    meta.ReconMethodName            = '3D Reprojection';
    meta.ReconMethodParameterLabels = ["none"];
    meta.ReconParameterUnits        = ["none"];
    meta.ReconMethodParameterValues = [0];
    meta.ReconFilterType            = "none";
    meta.ReconFilterSize            = 0;
    meta.AttenuationCorrection     = '2D-acquired transmission scan with a 68Ge pin';

    dcm2niix4pet(fullfile(source,'GeneralElectricAdvance-JHU'),...
        meta,'o',fullfile(destination,['sub-GeneralElectricAdvanceJHU' filesep 'pet'])); 
     
catch
    disp(message);
end

%% Chesapeake Medical Imaging
% ----------------------------------------------

% Canon Cartesion Prime PET-CT
% ----------------------

try
    clear meta
    meta.TimeZero                   = 'ScanStart';
    meta.Manufacturer               = 'Canon Medical Systems';
    meta.ManufacturersModelName     = 'Cartesion Prime';
    meta.InstitutionName            = 'Chesapeake Medical Imaging, USA';
    meta.BodyPart                   = 'Phantom';
    meta.Units                      = 'Bq/mL';
    meta.TracerName                 = 'FDG';
    meta.TracerRadionuclide         = 'F18';
    meta.InjectedRadioactivity      = 0.87;
    meta.InjectedRadioactivityUnits = 'mCi';
    meta.SpecificRadioactivity      = 'n/a';
    meta.SpecificRadioactivityUnits = 'n/a';
    meta.ModeOfAdministration       = 'infusion';
    meta.ScanStart                  = 0;
    meta.InjectionStart             = -2312;
    meta.FrameTimesStart            = [0 300 600 900];
    meta.AcquisitionMode            = 'list mode';
    meta.ImageDecayCorrected        = 'true';
    meta.ImageDecayCorrectionTime   = 0;
    meta.ReconMethodParameterLabels = ["subsets" "iterations"];
    meta.ReconMethodParameterLabels = ["none" "none"];
    meta.ReconMethodParameterValues = [24 5];
    meta.ReconFilterType            = "Gaussian";
    meta.ReconFilterSize            = 4;

    dcm2niix4pet(fullfile(source,'CanonCartesionPrimePETCT-NIA'),...
        meta,'o',fullfile(destination,['sub-CanonCartesionPrimeNIA' filesep 'pet'])); 
     
catch
    disp(message);
end
