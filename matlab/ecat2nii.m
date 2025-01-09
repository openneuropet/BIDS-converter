function FileListOut = ecat2nii(FileListIn,MetaList,varargin)

% Converts ECAT 7 image file from hrrt pet scanner (ecat format)
% to nifti image files + json
%
% :format: - FileListOut = ecat2nii(FileListIn,MetaList)
%          - FileListOut = ecat2nii(FileListIn,MetaList,options)
%
% :param FileListIn: a name or a Cell array of characters with paths and filenames
% :param MetaList: a structure or Cell array of structures for metadata
%   (a single structure can be use other many FileListIn - see examples)
%   options are name/value pairs
% :param FileListOut: a name or cell array of characters with filenames
%   (with path if the path out is different)
% :param sifout: is true or false (default) to output a sif file, default = false, 0/1 to indicate
%    SIF is a simple ascii file that contains the PET frame start and end times,
%    and the numbers of observed events during each PET time frame.
% :param gz: is true (default) or false to output .nii.gz or .nii
% :param savemat: is true or false (default) to save the ecat data as .mat
%
% :returns FileListOut: is the name or a cell array of names of the nifti files created
%        (should be the same as FileListOut entered as option with the added proper extension .nii or .nii.gz)
%
% .. code-block::
%
%   Example Meta = get_pet_metadata('Scanner','SiemensHRRT','TimeZero','ScanStart','TracerName','DASB','TracerRadionuclide','C11', ...
%                      'ModeOfAdministration','bolus','InjectedRadioactivity', 605.3220,'InjectedMass', 1.5934,'MolarActivity', 107.66)
%   FileListOut = ecat2nii(EcatFile,Meta,'FileListOut',ConvertedRenamedFile1);
%   FileListOut = ecat2nii({EcatFile1,EcatFile2},Meta,'gz',false,'sifout',true);
%   FileListOut = ecat2nii({EcatFile1,EcatFile2},{Meta1,Meta2},'FileListOut',{ConvertedRenamedFile1,ConvertedRenamedFile2}));``
%
% .. note::
%
%    Uses: readECAT7.m (Raymond Muzic, 2002)
%          jsonwrite.m (Guillaume Flandin, 2020)
%          nii_tool.m (Xiangrui Li, 2016)
%
%    See also get_pet_metadata.m to generate the metadata structure
%
% | *Claus Svarer, Martin Nørgaard, Chris Rorden & Cyril Pernet - 2021*
% | *Copyright Open NeuroPET team*

%% defaults
% ---------

warning on % set to off to ignore our useful warnings
sifout  = false; % 0/1 to indicate if sif file are also created
gz      = true;  % compress nifti
savemat = false; % save ecat data as .mat

%% debebugging
% ------------
ecat_save_steps = getenv('ECAT_SAVE_STEPS');
ecat_save_steps_dir = mfilename('fullpath');
if contains(ecat_save_steps_dir, 'LiveEditorEvaluationHelper')
    ecat_save_steps_dir = matlab.desktop.editor.getActiveFilename;
end
parts = strsplit(ecat_save_steps_dir, filesep);
ecat_save_steps_dir = strjoin([parts(1:end-2), 'ecat_testing', 'steps'], filesep);

%% initialize telemetry variable for reporting
telemetry_data = {};
telemetry_data.description = "Matlab_ecat2nii";

%% check inputs
% ------------

if nargin<=1
    if nargin == 1
        warning('only 1 argument in, missing input')
    end
    help ecat2nii
    return
end

if ~iscell(FileListIn)
    if ischar(FileListIn) && size(FileListIn,1)==1
        tmp = FileListIn; clear FileListIn;
        FileListIn{1} = tmp; clear tmp;
    else
        error('1st argument in must be a cell array of file names')
    end
end

if ~iscell(MetaList)
    if isstruct(MetaList) && size(MetaList,1)==1
        tmp = MetaList; clear MetaList;
        MetaList{1} = tmp; clear tmp;
    else
        error('1st argument in must be a cell array of file names')
    end
end

if iscell(MetaList) && any(size(MetaList)~=size(FileListIn))
    if size(MetaList,1) ==1
        disp('Replicating metadata for all input')
        tmp = MetaList; clear MetaList;
        MetaList = cell(size(FileListIn));
        for f=1:size(MetaList,1)
            MetaList{f} = tmp;
        end
        cleat tmp
    else
        error('2nd argument in must be a cell array of metadata structures')
    end
end

for v=1:length(varargin)
    if strcmpi(varargin{v},'FileListOut')
        FileListOut = varargin{v+1};
    elseif strcmpi(varargin{v},'sifout')
        sifout = varargin{v+1};
    elseif strcmpi(varargin{v},'gz')
        gz = varargin{v+1};
    elseif strcmpi(varargin{v},'savemat')
        savemat = varargin{v+1};
    elseif strcmpi(varargin{v},'notrack')
        setenv('TELEMETRY_ENABLED', 'False')
    end
end

if exist('FileListOut','var')
    if ~iscell(FileListOut)
        if ischar(FileListOut) && size(FileListOut,1)==1
            tmp = FileListOut; clear FileListOut;
            FileListOut{1} = tmp; clear tmp;
        else
            error('Name(s) argument must be a cell array of file names')
        end
    end
    
    if any(size(FileListOut)~=size(FileListIn))
        error('The number of files in (FileListIn) does not match the number of file names to create')
    end
end

%% Read and write data
% --------------------
for j=1:length(FileListIn)

    try
        fprintf('Conversion of file: %s\n',FileListIn{j});

        % quickly ensure we have the TimeZero - key to all analyzes!
        info     = MetaList{1};
        if ~isfield(info,'TimeZero')
            error_text = 'Metadata TimeZero is missing - set to ScanStart or empty to use the scanning time as injection time';
            telemetry_data.returncode = 1;
            telemetry_data.error = error_text;
            telemetry(telemetry_data, FileListIn{j})
            error(error_text)
        end
        
        % Read ECAT file headers
        if ~exist(FileListIn{j},'file')
            error('the file %s does not exist',FileListIn{j}),
        end
        
        [pet_path,pet_file,ext] = fileparts(FileListIn{j});
        if strcmp(ext,'.gz')
            newfile             = gunzip([pet_path filesep pet_file ext]);
            [~,pet_file,ext]    = fileparts(newfile{1});
        end
        
        pet_file = [pet_file ext];
        [mh,sh,data]  = readECAT7([pet_path filesep pet_file]); % loading the whole file here and iterating to flipdim below only minuimally improves time (0.6sec on NRU server)
        if (ecat_save_steps == '1')
            first_middle_last_frames_to_text_cell(data,ecat_save_steps_dir, '6_ecat2nii_matlab');
        end
        if sh{1}.data_type ~= 6
            error('Conversion for 16 bit data only (type 6 in ecat file) - error loading ecat file');
        end
        Nframes  = mh.num_frames;
        
        % Create data reading 1 frame at a time - APPLYING THE SCALE FACTOR
        img_temp = zeros(sh{1}.x_dimension,sh{1}.y_dimension,sh{1}.z_dimension,Nframes);
        for i=Nframes:-1:1
            fprintf('Working at frame: %i\n',i);
            [mh,shf,data]     = readECAT7([pet_path filesep pet_file],i);
            img_temp(:,:,:,i) = flipdim(flipdim(flipdim((double(cat(4,data{:}))*shf{1}.scale_factor),2),3),1); %#ok<DFLIPDIM>
            % also get timing information
            Start(i)          = shf{1}.frame_start_time*60;
            DeltaTime(i)      = shf{1}.frame_duration*60;
            if mh.sw_version >=73
                Prompts(i)    = shf{1}.prompt_rate*shf{1}.frame_duration*60;
                Randoms(i)    = shf{1}.random_rate*shf{1}.frame_duration*60;
            else
                Prompts(i)    = 0;
                Randoms(i)    = 0;
            end
        end

        % capture ecat version
        telemetry_data.InputType = append("ECAT", string(mh.sw_version));

        % save debugging steps 6 and 7
        if (ecat_save_steps == '1')
            first_middle_last_frames_to_text_cell(data,ecat_save_steps_dir, '6_ecat2nii_matlab');
            first_middle_last_frames_to_text(img_temp,ecat_save_steps_dir, '7_flip_ecat2nii_matlab');
        end

        % rescale to 16 bits
        rg = max(img_temp(:))-min(img_temp(:));
        if rg ~= 32767 % same as range(img_temp(:)) but no need of stats toolbox
            MaxImg       = max(img_temp(:));
            img_temp     = img_temp/MaxImg*32767;
            Sca          = MaxImg/32767;
            MinImg       = min(img_temp(:));
            if (MinImg<-32768)
                img_temp = img_temp/MinImg*(-32768);
                Sca      = Sca*MinImg/(-32768);
            end

            % % save scaling factor to file located at ecat_save_steps_dir/8.5_sca_matlab.txt
            % fid = fopen([ecat_save_steps_dir filesep '8.5_sca_matlab.txt'],'w');
            % fprintf(fid,'Scaling factor: %10e\n',Sca);
            % x = mh.ecat_calibration_factor * Sca;
            % fprintf(fid,'Scaling factor * ECAT Cal Factor: %10.10f\n',x);
            % fclose(fid);
        end

        % save debugging step 8 - rescale to 16 bits
        if (ecat_save_steps == '1')
            first_middle_last_frames_to_text(img_temp,ecat_save_steps_dir, '8_rescale_to_16_ecat2nii_matlab');
        end

        % check names
        if ~exist('FileListOut','var')
            [~,pet_filename]           = fileparts(pet_file);
        else
            [newpet_path,pet_filename] = fileparts(FileListOut{j});
            if ~isempty(newpet_path)
                pet_path = newpet_path;
            end
        end
        
        filenameout  = [pet_path filesep pet_filename];
        if ~exist(fileparts(filenameout),'dir')
            mkdir(fileparts(filenameout))
        end
        
        % write timing info separately
        if sifout
            pid = fopen([filenameout '.sif'],'w');
            
            if (pid~=0)
                offset   = tzoffset(datetime(mh.scan_start_time, 'ConvertFrom', 'posixtime','TimeZone','local'));
                scantime = datetime(mh.scan_start_time, 'ConvertFrom', 'posixtime','TimeZone','UTC') + offset;
                if offset ~=0
                    warning('sif scantime is adjusted by local time difference to UTC: %s',offset)
                end
                fprintf(pid,'%s %i 4 1\n',scantime, length(Start));
                for i=1:length(Start)
                    fprintf(pid,'%i %i %i %i\n',round(Start(i)),round(Start(i)+DeltaTime(i)),...
                        round(Prompts(i)),round(Randoms(i)));
                end
                fclose(pid);
            end
        end
        
        % save raw data
        if savemat or ecat_save_steps == '1'
            if mh.calibration_units == 1 % see line 337
                ecat = img_temp.*Sca;
            else
                ecat = img_temp.*(Sca*mh.ecat_calibration_factor);
            end
            save([filenameout '.ecat.mat'],'ecat','-v7.3');
        end
        
        % write nifti format + json
        if isfield(sh{1,1},'annotation')
            if ~isempty(deblank(sh{1,1}.annotation))
                [info.ReconMethodName,i,s]            = get_recon_method(deblank(sh{1,1}.annotation));
                if ~isempty(i) && ~isempty(s)
                    info.ReconMethodParameterLabels   = {'iterations', 'subsets', 'lower_threshold', 'upper_threshold'};
                    info.ReconMethodParameterUnits    = {'none', 'none', 'keV', 'keV'};
                    info.ReconMethodParameterValues   = [str2double(i), str2double(s), mh.lwr_true_thres, mh.upr_true_thres];
                else % some method without iteration and subset e.g. back projection
                    info.ReconMethodParameterLabels   = {'lower_threshold', 'upper_threshold'};
                    info.ReconMethodParameterUnits    = {'keV', 'keV'};
                    info.ReconMethodParameterValues   = [mh.lwr_true_thres, mh.upr_true_thres];
                end
                
            else % annotation is blank - no info on method
                if isfield(info.ReconMethodName) % user provided
                    [info.ReconMethodName,i,s] = get_recon_method(deblank(info.ReconMethodName));
                    if ~isempty(i) && ~isempty(s)
                        info.ReconMethodParameterLabels   = {'iterations', 'subsets', 'lower_threshold', 'upper_threshold'};
                        info.ReconMethodParameterUnits    = {'none', 'none', 'keV', 'keV'};
                        info.ReconMethodParameterValues   = [str2double(i), str2double(s), mh.lwr_true_thres, mh.upr_true_thres];
                    else % some method without iteration and subset e.g. back projection
                        info.ReconMethodParameterLabels   = {'lower_threshold', 'upper_threshold'};
                        info.ReconMethodParameterUnits    = {'keV', 'keV'};
                        info.ReconMethodParameterValues   = [mh.lwr_true_thres, mh.upr_true_thres];
                    end
                else
                    warning('no reconstruction method information found - invalid BIDS metadata')
                    info.ReconMethodParameterLabels   = {'lower_threshold', 'upper_threshold'};
                    info.ReconMethodParameterUnits    = {'keV', 'keV'};
                    info.ReconMethodParameterValues   = [mh.lwr_true_thres, mh.upr_true_thres];
                end
            end
            
        else % no info on method
            warning('no reconstruction method information found - invalid BIDS metadata')
            info.ReconMethodParameterLabels   = {'lower_threshold', 'upper_threshold'};
            info.ReconMethodParameterUnits    = {'keV', 'keV'};
            info.ReconMethodParameterValues   = [mh.lwr_true_thres, mh.upr_true_thres];
        end
        
        for idx = 1:numel(sh)
            info.ScaleFactor(idx,1)           = 1; % because we apply sh{idx}.scale_factor;
            info.ScatterFraction(idx,1)       = sh{idx}.scatter_fraction;
            info.DecayCorrectionFactor(idx,1) = sh{idx}.decay_corr_fctr;
            info.PromptRate(idx,1)            = sh{idx}.prompt_rate;
            info.RandomRate(idx,1)            = sh{idx}.random_rate;
            info.SinglesRate(idx,1)           = sh{idx}.singles_rate;
        end
        info.FrameDuration                    = DeltaTime';
        info.FrameTimesStart                  = zeros(size(info.FrameDuration));
        info.FrameTimesStart(2:end)           = cumsum(info.FrameDuration(1:end-1));
        
        % Time stuff, time zero is kinda required [] or 'ScanStart' or actual value
        if isempty(info.TimeZero) || strcmp(info.TimeZero,'ScanStart')
            offset                            = tzoffset(datetime(mh.scan_start_time, 'ConvertFrom', 'posixtime','TimeZone','local'));
            info.TimeZero                     = datestr((datetime(mh.scan_start_time, 'ConvertFrom', 'posixtime','TimeZone','UTC') + offset),'hh:mm:ss');
            if offset ~=0
                warning('TimeZero is set to be scan time adjusted by local time difference to UTC: %s',offset)
            end
        end
        
        % if not specified we infer that injection and scan are together the time zero
        if ~isfield(info,'ScanStart')
            info.ScanStart                    = 0;
        end
        
        if ~isfield(info,'InjectionStart')
            info.InjectionStart               = 0;
        end
        
        info.DoseCalibrationFactor            = Sca*mh.ecat_calibration_factor;
        info.Filemoddate                      = datestr(now);
        info.Version                          = 'NIfTI1';
        info.ConversionSoftware               = 'ecat2nii.m';
        info.Description                      = 'Open NeuroPET ecat7+ matlab based conversion';
        info.ImageSize                        = [sh{1}.x_dimension sh{1}.y_dimension sh{1}.z_dimension mh.num_frames];
        info.PixelDimensions                  = [sh{1}.x_pixel_size sh{1}.y_pixel_size sh{1}.z_pixel_size 0].*10;
        info                                  = orderfields(info);
        
        % check radiotracer info - should have been done already in
        % get_pet_metadata ; but user can also populate metadata by hand
        % so let's recheck
        if ~isfield(info,'Units')
            info.Units = 'Bq/mL';
        end
        
        radioinputs = {'InjectedRadioactivity', 'InjectedMass', ...
            'SpecificRadioactivity', 'MolarActivity', 'MolecularWeight'};
        input_check            = cellfun(@(x) isfield(info,x), radioinputs);
        index                  = 1; % make key-value pairs
        arguments              = cell(1,sum(input_check)*2);
        if sum(input_check) ~= 0
            for r=find(input_check)
                arguments{index}   = radioinputs{r};
                arguments{index+1} = info.(radioinputs{r});
                index = index + 2;
            end
            dataout                = check_metaradioinputs(arguments);
            datafieldnames         = fieldnames(dataout);
            
            % set new info fields
            for f = 1:size(datafieldnames,1)
                if ~isfield(info,datafieldnames{f})
                    info.(datafieldnames{f}) = dataout.(datafieldnames{f});
                end
            end
        end
        
        % write json file using jsonwrite from Guillaume Flandin
        % $Id: spm_jsonwrite.m
        if ~contains(filenameout,'_pet')
            jsonwrite([filenameout '_pet.json'],info)
            status = updatejsonpetfile([filenameout '_pet.json']); % validate
        else
            jsonwrite([filenameout '.json'],info)
            status = updatejsonpetfile([filenameout '.json']); % validate
        end
        
        if status.state ~= 1
            warning('the json file is BIDS invalid')
        end
        
        if mh.calibration_units == 1 % do calibrate
            img_temp                          = single(round(img_temp).*(Sca*mh.ecat_calibration_factor)); % scale and dose calibrated
            if ecat_save_steps == '1'
                first_middle_last_frames_to_text(img_temp,ecat_save_steps_dir, '9_scal_cal_units_ecat2nii_matlab');
            end
            warning('it looks like the source data are not dose calibrated - ecat2nii is thus scaling the data')
        else % do not calibrate
            img_temp                          = single(round(img_temp).*Sca); % just the 16 bit scaling, img_temp is already dose calibrated
            warning('it looks like the source data are already dose calibrated - ecat2nii is thus not scaling the data')
        end
        info.Datatype                         = 'single';
        info.BitsPerPixel                     = 32;
        info.SpaceUnits                       = 'Millimeter';
        info.TimeUnits                        = 'Second';
        info.SliceCode                        = 'Unknown';
        info.FrequencyDimension               = 0;
        info.PhaseDimension                   = 0;
        info.SpatialDimension                 = 0;
        info.AdditiveOffset                   = 0;
        info.MultiplicativeScaling            = 0;
        info.TimeOffset                       = 0;
        info.DisplayIntensityRange            = [0 0];
        info.TransformName                    = 'Sform';
        info.Transform.Dimensionality         = 3;
        info.Qfactor                          = 1; % determinant of the rotation matrix
        
        % map https://nifti.nimh.nih.gov/pub/dist/src/niftilib/nifti1.h
        info.raw.sizeof_hdr     = 348;
        info.raw.dim_info       = '';
        info.raw.dim            = [4 sh{1}.x_dimension sh{1}.y_dimension sh{1}.z_dimension mh.num_frames 1 1 1];
        info.raw.intent_p1      = 0;
        info.raw.intent_p2      = 0;
        info.raw.intent_p3      = 0;
        info.raw.intent_code    = 0;
        info.raw.datatype       = 16;
        info.raw.bitpix         = 32;
        info.raw.slice_start    = 0;
        info.raw.pixdim         = [1 sh{1}.x_pixel_size*10 sh{1}.y_pixel_size*10 sh{1}.z_pixel_size*10 0 0 0 0];
        info.raw.vox_offset     = 352;
        info.raw.scl_slope      = 0; % this is where the DoseCalibrationFactor could be set rather than in the data
        info.raw.scl_inter      = 0;
        info.raw.slice_end      = 0;
        info.raw.slice_code     = 0;
        info.raw.xyzt_units     = 10;
        info.raw.cal_max        = max(img_temp(:));
        info.raw.cal_min        = min(img_temp(:));
        info.raw.slice_duration = 0;
        info.raw.toffset        = 0;
        info.raw.descrip        = 'Open NeuroPET ecat2nii.m conversion';
        info.raw.aux_file       = '';
        info.raw.qform_code     = 0;
        info.raw.sform_code     = 1; % 0: Arbitrary coordinates; 1: Scanner-based anatomical coordinates; 2: Coordinates aligned to another file's, or to anatomical "truth" (coregistration); 3: Coordinates aligned to Talairach-Tournoux Atlas; 4: MNI 152 normalized coordinates
        info.raw.quatern_b      = 0;
        info.raw.quatern_c      = 0;
        info.raw.quatern_d      = 0;
        info.raw.qoffset_x      = -1*(((sh{1}.x_dimension*sh{1}.x_pixel_size*10)/2)-(sh{1}.x_pixel_size*5));
        info.raw.qoffset_y      = -1*(((sh{1}.y_dimension*sh{1}.y_pixel_size*10)/2)-(sh{1}.y_pixel_size*5));
        info.raw.qoffset_z      = -1*(((sh{1}.z_dimension*sh{1}.z_pixel_size*10)/2)-(sh{1}.z_pixel_size*5));
        info.raw.srow_x         = [sh{1}.x_pixel_size*10 0 0 info.raw.qoffset_x];
        info.raw.srow_y         = [0 sh{1}.y_pixel_size*10 0 info.raw.qoffset_y];
        info.raw.srow_z         = [0 0 sh{1}.z_pixel_size*10 info.raw.qoffset_z];
        T                       = eye(4);
        T([1 6 11])             = [sh{1}.x_pixel_size*10 sh{1}.y_pixel_size*10 sh{1}.z_pixel_size*10];
        T([4 8 12])             = [info.raw.qoffset_x info.raw.qoffset_y info.raw.qoffset_z];
        info.Transform.T        = T;
        info.raw.intent_name    = '';
        info.raw.magic          = 'n+1 ';
        
        % write nifti file using nii_tool
        % Copyright (c) 2016, Xiangrui Li https://github.com/xiangruili/dicm2nii
        % BSD-2-Clause License
        nii.hdr                 = info.raw;
        nii.img                 = img_temp;
        % add _pet if needed
        if ~contains(filenameout,'_pet')
            fnm                 = [filenameout '_pet.nii'];
        else
            fnm                 = [filenameout '.nii'];
        end
        
        % compress if requested
        if gz
            fnm = [fnm '.gz']; %#ok<*AGROW>
        end


        if ecat_save_steps == '1'
            first_middle_last_frames_to_text(img_temp, ecat_save_steps_dir, '10_save_nii_cat2nii_matlab');
        end
        nii_tool('save', nii, fnm);
        FileListOut{j} = fnm;

        if ecat_save_steps == '1'
            % open the nifti file just written and check to see if the written values differ from the original
            nii = nii_tool('load', fnm);
            first_middle_last_frames_to_text(nii.img, ecat_save_steps_dir, '11_read_saved_nii_matlab');
        end
        
        % optionally one can use niftiwrite from the Image Processing Toolbox
        % warning different versions of matlab may provide different nifti results
        % this is kept here allowing to uncomment to compare results
        %
        % if gz
        %     niftiwrite(img_temp,[filenameout '.nii'],info,'Endian','little','Compressed',true);
        %     FileListOut{j} = [filenameout '_pet.nii.gz']; %#ok<*AGROW>
        % else
        %     FileListOut{j} = [filenameout '_pet.nii'];
        %     niftiwrite(img_temp,FileListOut{j},info,'Endian','little','Compressed',false);
        % end

        telemetry_data.returncode = 0;
        telemetry(telemetry_data, FileListIn{j});
        
    catch conversionerr
        telemetry_data.returncode = 1;
        telemetry_data.error = conversionerr.message;
        telemetry(telemetry_data, FileListIn{j});
        FileListOut{j} = sprintf('%s failed to convert:%s',FileListIn{j},conversionerr.message, conversionerr.stack.line);
    end
    
    if exist('newfile','var') % i.e. decompressed .nii.gz
        delete(newfile{1});
    end
end
