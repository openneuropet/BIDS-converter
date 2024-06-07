function [mh,sh,data] = readECAT7(fs,matrix,varargin)

% Read the main header, subheaders, and image\/sinogram data from
% ECAT v 7.x \*.v, \*.i, \*.S, and \*.a files.
%
%  :format: [mh,sh,data] = readECAT(fs, [matrix], ['Calibrated', 'on'])
%
%  :param fs: (optional) file specification (name/path) of file to read.  if
%     file specification is not given, then user is prompted to select a file.
%  :param matrix: (optional) vector of matrix numbers to read.  Default = all matrices in file.
%  :param Calibrated': 'on' or 'off', if on it calibrates to pixel values in units given in mh.data_units.
%                         When 'Calibrated' is 'on', pixel values are stored as doubles;
%                         otherwise, pixels are int16.  Calibration is achieved
%                         by multiplication of pixels by ecat_calibration_factor
%                         (in mh) and the scale_factor (in sh).
%                         The default is uncalibrated in which case pixels are int16.
%
% :returns: - mh   \- main header
%           - sh   \- cell array of subheaders.  sh{i} is subheader for matrix(i).
%           - data \- cell array containing pixel data.  data{i} is a
%                 [rows, cols, planes] or [proj, views, planes] array with the
%                 data of matrix i. The data are stored in the file as 2 byte signed integers.
%
% .. note:: 
%
%   To convert data from cell array of 3D arrays to a 4D array: d=double(cat(4,data{:}));
%   This could be helpful to convert a time-sequence of image volumes to something
%   that can be more easily manipulated.
%
%   This should work for the entire line of ECAT scanners running 7.x of the software.
%
%   Original version written by BT Christian, 12/10/98
%
%   Overhaul by RF Muzic, 20000726
%
%   Revised by RF Muzic, 20010916
%
%   Revised by RF Muzic, 20011221 add support for 3D sinogram files (prev only images supported)
%
%   Revised by RF Muzic, 20021017 generalize support from multiple frames to multiple
%   matrices.  The distinction is that a matrix could correspond to
%   different bed position or different frame.
%
%   Revised by RF Muzic, 20021029 correct length of last fill block in image file subheader.
%   It is actually 49 shorts (to make a 512 byte sh block) whereas CTI docs says 48.
%   Add support for .a files.
%
%   Copyright ? 2002 Raymond F. Muzic, Jr.
%
%   Not intended for clinical/diagnostic use.  User assumes all risk.

persistent lastpath_

if nargin == 0
    fs = [];
end

%ecat_save_steps = '1'

if length(fs) == 0
    origpwd = pwd;
    if length(lastpath_) > 0; cd(lastpath_); end
    [fn,pat]=uigetfile({'*.v;*.S;*.i;*.a', 'All ECAT 7 Files (*.v, *.S, *.i, *.a)'; '*.*',    'All Files (*.*)'}, 'Select a file');
    fs = [pat fn];
    if isa(pat, 'uint8'), lastpath_ = pat; end
    cd(origpwd);
end

matlabVersion=sscanf(version,'%f');

% handle options
calibrated = 0;
if length(varargin) > 0
    lvarargin = lower(varargin);
    idx = strmatch('calibrated', lvarargin{1});
    if length(idx) > 0
        calibrated = strcmp(lvarargin{idx+1}, 'on');
    end
end

% open file as ieee big-endian
file_endianess = 'ieee-be';
fid = fopen(fs,'r', file_endianess);
if (fid < 0)
    error('readECAT: Problem opening file %s', fs);
end


%  Read in the main header info
mh = readMainheader(fid);

ecat_save_steps = getenv('ECAT_SAVE_STEPS');
ecat_save_steps_dir = mfilename('fullpath');
if contains(ecat_save_steps_dir, 'LiveEditorEvaluationHelper')
    ecat_save_steps_dir = matlab.desktop.editor.getActiveFilename;
end
parts = strsplit(ecat_save_steps_dir, filesep);
ecat_save_steps_dir = strjoin([parts(1:end-2), 'ecat_testing', 'steps'], filesep);

% save main header output to json
if (ecat_save_steps == '1')
    % save main header
    main_header_json = (jsonencode(mh, PrettyPrint=true));
    step_1_file = fopen([ecat_save_steps_dir filesep '1_read_mh_ecat_matlab.json'], 'w');
    fprintf(step_1_file, '%s', main_header_json);
    fclose(step_1_file);
end

if (nargout == 1)
    return
end


%  Read in the directory list
pos   = 512;
ndr   = 0; % number of directory records
direc = [];
while (1)
    fseek(fid,pos,-1);
    buff = fread(fid,[4 32],'int32');  % read directory
    if (buff(4,1) == 0)
        break
    end
    ndr   = ndr + 1;
    direc = [direc buff(:,2:(buff(4,1)+1))];
    if (buff(2,1) == 2)
        break
    end
    pos = (buff(2,1)-1)*512;
end

% sort based on matrix number as occasionally they are stored out of order
[~,idx]  = sort(direc(1,:));
dirtable = direc(:,idx);

% when matrix is not specified or is [], default if to read all matrices
if (nargin < 2)
    matrix = 1:size(direc,2);  % default is all matrices
end
if (length(matrix) == 0)
    matrix = 1:size(direc,2);  % default is all matrices
end

nmat = length(matrix);  % number of matrices to return

if any((matrix(1:nmat) > size(direc,2)) | (matrix(1:nmat) < 1))
    error('readECAT7: Matrix numbers must be <= %d and >= %d', 1, nmat);
end

sh   = cell(nmat,1);
data = cell(nmat,1);
pixel_data_type = '';

% select proper sh routine
switch mh.file_type
    case 3
        readSubheader = 'readSubheaderAttenuation';
    case 7
        readSubheader = 'readSubheaderImage';
    case 11
        readSubheader = 'readSubheader3DScan';
    otherwise
        warning('Do not know how to read this type of file.')
        % Beware: in some file types pixels are stored as floats.
        % To support reading them, fread will have to be called with 'float' format when appropriate.
end

% Loop over matrices reading subheader and pixel data
sh = cell([nmat 1]);
for m = 1:nmat
    midx = matrix(m);
    
    % attempt to read all matrices irrespective of 'code' in
    % this may allow one to access "deleted" data not seen by CTI  software
    %    code =  1 if matrix exists, access = read/write
    %            0 if data not yet written
    %           -1 if matrix deleted, access = none
    % See notes on dirtable in writeECAT7
    
    % jump to subheader
    fseek(fid,512*(dirtable(2,midx)-1),-1);   % especially needed if
    % last block of previous dataset is not completely filled
    
    % read and parse subheader and advance file position to pixel data
    fp = ftell(fid);
    [sh{m}, sz] = feval(readSubheader, fid, dirtable(:,m));
    if rem(ftell(fid)-fp, 512)
        warning(['readECAT7: There is a problem in subheader read.'  ...
            'Subheader size should be a multiple of 512 bytes.']);
    end
    
    if (nargout > 2)  % if user asked for pixel data
        
        switch sh{m}.data_type
            case 5 % IEEE float (32 bit)
                data{m} = fread(fid, [sz(1)*sz(2) sz(3)],'float32');
                pixel_data_type = 'float32';
            case 6 % SUN int16
                if (matlabVersion(1) < 6)
                    warning('old matlab version, using int16 to read')
                    data{m} = int16(fread(fid, [sz(1)*sz(2) sz(3)],'int16'));
                    pixel_data_type = 'int16';
                else
                    data{m} = fread(fid, [sz(1)*sz(2) sz(3)],'int16=>int16');
                    pixel_data_type = 'int16=>int16';
                end
            otherwise
                warning('readECAT7: unrecognized data type');
                pixel_data_type = 'unrecognized data type';
        end
        % other sh{m}.data_type: 2 = VAX int16,  3 = VAX int32,  4 = VAX F-float (32 bit),  7 = SUN int32
        
        data{m} = reshape(data{m}, [sz(1) sz(2) sz(3)]);
        
        if calibrated  % convert to double pixels and scale to mh.data_units
            cf = sh{m}.scale_factor*mh.ecat_calibration_factor;  % calibration factor for mh.data_units
            data{m} = cf*data{m};
        end
        
    end % if nargout > 2
end  % loop over matrices

fclose(fid);
if (ecat_save_steps == '1')
    % save subheaders header
    sub_header_json = (jsonencode(sh, PrettyPrint=true));
    step_2_file = fopen([ecat_save_steps_dir filesep '1_read_sh_ecat_matlab.json'], 'w');
    fprintf(step_2_file, '%s', sub_header_json);
    fclose(step_2_file);

    % write out endianess and datatype of the pixel data matrix
    step_3_struct = {};
    x.data_type = class(data{1});
    x.endianess = file_endianess;
    step_3_json = (jsonencode(x, PrettyPrint=true));
    step_3_file = fopen([ecat_save_steps_dir filesep '3_determine_data_type_matlab.json'], 'w');
    fprintf(step_3_file, '%s', step_3_json);
    fclose(step_3_file);

    first_middle_last_frames_to_text_cell(data, ecat_save_steps_dir, '4_read_img_ecat_matlab')

    % scale if calibrated
    % data has already been saved in the previous step (step 4) but we go ahead and do this step once more because the
    % numbering system that's been imposed upon us to test these outputs
    if calibrated ~0
        first_middle_last_frames_to_text_cell(data, ecat_save_steps_dir, '5_scale_img_ecat_matlab')
    end
end

return

function mh = readMainheader(fid)

mh.magic_number               = char(fread(fid,14,'uint8')');
mh.original_file_name         = char(fread(fid,32,'uint8')');
mh.sw_version                 = fread(fid,1,'int16');
mh.system_type                = fread(fid,1,'int16');
mh.file_type                  = fread(fid,1,'int16');
mh.serial_number              = char(fread(fid,10,'uint8')');
mh.scan_start_time            = fread(fid,1,'int32'); % seconds from 1/1/1970 GMT+0
% To get local date/time in Cleveland (EST), set tzo=-5/24 (since EST = GMT -5) then
% dv=datevec(mh.scan_start_time/(24*60*60)+datenum('1/1/1970')+tzo)
%    where dv=[yr month date hr min sec]

mh.isotope_name               = char(fread(fid,8,'uint8')');
mh.isotope_halflife           = fread(fid,1,'float32');
mh.radiopharmaceutical        = char(fread(fid,32,'uint8')');
mh.gantry_tilt                = fread(fid,1,'float32');
mh.gantry_rotation            = fread(fid,1,'float32');
mh.bed_elevation              = fread(fid,1,'float32');
mh.intrinsic_tilt             = fread(fid,1,'float32');
mh.wobble_speed               = fread(fid,1,'int16');
mh.transm_source_type         = fread(fid,1,'int16');
mh.distance_scanned           = fread(fid,1,'float32');
mh.transaxial_fov             = fread(fid,1,'float32');
mh.angular_compression        = fread(fid,1,'int16');
mh.coin_samp_mode             = fread(fid,1,'int16');
mh.axial_samp_mode            = fread(fid,1,'int16');
mh.ecat_calibration_factor    = fread(fid,1,'float32');
mh.calibration_units          = fread(fid,1,'int16');
mh.calibration_units_label    = fread(fid,1,'int16');
mh.compression_code           = fread(fid,1,'int16');
mh.stud_type                  = char(fread(fid,12,'uint8')');
mh.patient_id                 = char(fread(fid,16,'uint8')');
mh.patient_name               = char(fread(fid,32,'uint8')');
mh.patient_sex                = char(fread(fid,1,'uint8')');
mh.patient_dexterity          = char(fread(fid,1,'uint8')');
mh.patient_age                = fread(fid,1,'float32');
mh.patient_height             = fread(fid,1,'float32');
mh.patient_weight             = fread(fid,1,'float32');
mh.patient_birth_date         = fread(fid,1,'int32');
mh.physician_name             = char(fread(fid,32,'uint8')');
mh.operator_name              = char(fread(fid,32,'uint8')');
mh.study_description          = char(fread(fid,32,'uint8')');
mh.acquisition_type           = fread(fid,1,'int16');
mh.patient_orientation        = fread(fid,1,'int16');
mh.facility_name              = char(fread(fid,20,'uint8')');
mh.num_planes                 = fread(fid,1,'int16');
mh.num_frames                 = fread(fid,1,'int16');
mh.num_gates                  = fread(fid,1,'int16');
mh.num_bed_pos                = fread(fid,1,'int16'); % starts at bed 0
mh.init_bed_position          = fread(fid,1,'float32');
mh.bed_position               = fread(fid,15,'float32');
mh.plane_separation           = fread(fid,1,'float32');
mh.lwr_sctr_thres             = fread(fid,1,'int16');
mh.lwr_true_thres             = fread(fid,1,'int16');
mh.upr_true_thres             = fread(fid,1,'int16');
mh.user_process_code          = char(fread(fid,10,'uint8')');
mh.acquisition_mode           = fread(fid,1,'int16');
mh.bin_size                   = fread(fid,1,'float32');
mh.branching_fraction         = fread(fid,1,'float32');
mh.dose_start_time            = fread(fid,1,'int32');
mh.dosage                     = fread(fid,1,'float32');
mh.well_counter_corr_factor   = fread(fid,1,'float32');
mh.data_units                 = char(fread(fid,32,'uint8')');  % e.g. 'Bq/cc'
mh.septa_state                = fread(fid,1,'int16');
mh.fill                       = fread(fid,6,'int16');
return


function [sh, sz] = readSubheader3DScan(fid, dirtable)
% fid = file identifier (of open file).  On input file position must correspond
%   to start of subheader.  On output, file will be positioned for reading pixel data.
% dirtable = directory record
% sh = subheader
% sz = [nx, ny, nz] = size of matrix that follows this subheader

% 3D sinogram data file
sh.data_type                 = fread(fid,1,'int16');
sh.num_dimensions            = fread(fid,1,'int16');
sh.num_r_elements            = fread(fid,1,'int16');
sh.num_angles                = fread(fid,1,'int16');
sh.corrections_applied       = fread(fid,1,'int16');
sh.num_z_elements            = fread(fid,64,'int16');
sh.ring_difference           = fread(fid,1,'int16');
sh.storage_order             = fread(fid,1,'int16');
sh.axial_compression         = fread(fid,1,'int16');
sh.x_resolution              = fread(fid,1,'float32');
sh.y_resolution              = fread(fid,1,'float32');
sh.z_resolution              = fread(fid,1,'float32');
sh.w_resolution              = fread(fid,1,'float32');
sh.fill                      = fread(fid,6,'int16');
sh.gate_duration             = fread(fid,1,'int32');
sh.r_wave_offset             = fread(fid,1,'int32');
sh.num_accepted_beats        = fread(fid,1,'int32');
sh.scale_factor              = fread(fid,1,'float32');
sh.scan_min                  = fread(fid,1,'int16');
sh.scan_max                  = fread(fid,1,'int16');
sh.prompts                   = fread(fid,1,'int32');
sh.delayed                   = fread(fid,1,'int32');
sh.multiples                 = fread(fid,1,'int32');
sh.net_trues                 = fread(fid,1,'int32');
sh.tot_avg_cor               = fread(fid,1,'float32');
sh.tot_avg_uncor             = fread(fid,1,'float32');
sh.tot_coin_rate             = fread(fid,1,'int32');
sh.frame_start_time          = fread(fid,1,'int32')/60000; % convert msec to min
sh.frame_duration            = fread(fid,1,'int32')/60000; % convert msec to min
sh.deadtime_correction_factor    = fread(fid,1,'float32');
sh.fill2                     = fread(fid,90,'int16');
sh.fill3                     = fread(fid,50,'int16');
sh.uncor_singles             = fread(fid,128,'float32');
sz = [sh.num_r_elements sh.num_angles (dirtable(3)-dirtable(2)-1)*512/sh.num_r_elements/sh.num_angles/2];
return

function [sh, sz] = readSubheaderImage(fid, dirtable)
% fid = file identifier (of open file).  On input file position must correspond
%   to start of subheader.  On output, file will be positioned for reading pixel data.
% dirtable = directory record
% sh = subheader
% sz = [nx, ny, nz] = size of matrix that follows this subheader

% image file
sh.data_type                 = fread(fid,1,'int16');
sh.num_dimensions            = fread(fid,1,'int16');
pixel_dimensions             = fread(fid,3,'int16');
sh.x_dimension               = pixel_dimensions(1);
sh.y_dimension               = pixel_dimensions(2);
sh.z_dimension               = pixel_dimensions(3);
pixel_offsets                = fread(fid,3,'float32');
sh.x_offset                  = pixel_offsets(1);
sh.y_offset                  = pixel_offsets(2);
sh.z_offset                  = pixel_offsets(3);
sh.recon_zoom                = fread(fid,1,'float32');
sh.scale_factor              = fread(fid,1,'float32');
sh.image_min                 = fread(fid,1,'int16');
sh.image_max                 = fread(fid,1,'int16');
pixel_sizes                  = fread(fid,3,'float32');
sh.x_pixel_size              = pixel_sizes(1);
sh.y_pixel_size              = pixel_sizes(2);
sh.z_pixel_size              = pixel_sizes(3);
sh.frame_duration            = fread(fid,1,'int32')/60000; % convert msec to min
sh.frame_start_time          = fread(fid,1,'int32')/60000; % convert msec to min
sh.filter_code               = fread(fid,1,'int16');
pixel_resolutions            = fread(fid,3,'float32');
sh.x_resolution              = pixel_resolutions(1);
sh.y_resolution              = pixel_resolutions(2);
sh.z_resolution              = pixel_resolutions(3);
sh.num_r_elements            = fread(fid,1,'float32');
sh.num_angles                = fread(fid,1,'float32');
sh.z_rotation_angle          = fread(fid,1,'float32');
sh.decay_corr_fctr           = fread(fid,1,'float32');
sh.processing_code           = fread(fid,1,'int32');
sh.gate_duration             = fread(fid,1,'int32');
sh.r_wave_offset             = fread(fid,1,'int32');
sh.num_accepted_beats        = fread(fid,1,'int32');
sh.filter_cutoff_frequency   = fread(fid,1,'float32');
sh.filter_resolution         = fread(fid,1,'float32');
sh.filter_ramp_slope         = fread(fid,1,'float32');
sh.filter_order              = fread(fid,1,'int16');
sh.filter_scatter_fraction   = fread(fid,1,'float32');
sh.filter_scatter_slope      = fread(fid,1,'float32');
sh.annotation                = char(fread(fid,40,'uint8')');
sh.transformation_matrix     = fread(fid,9,'float32');
sh.rfilter_cutoff            = fread(fid,1,'float32');
sh.rfilter_resolution        = fread(fid,1,'float32');
sh.rfilter_code              = fread(fid,1,'int16');
sh.rfilter_order             = fread(fid,1,'int16');
sh.zfilter_cutoff            = fread(fid,1,'float32');
sh.zfilter_resolution        = fread(fid,1,'float32');
sh.zfilter_code              = fread(fid,1,'int16');
sh.zfilter_order             = fread(fid,1,'int16');
sh.transformation_matrix2    = fread(fid,3,'float32');
sh.scatter_type              = fread(fid,1,'int16');
sh.recon_type                = fread(fid,1,'int16');
sh.recon_views               = fread(fid,1,'int16');
sh.prompt_rate               = fread(fid,1,'float32');   % [counts/sec]   total_prompt = prompt_rate*frame_duration */
sh.random_rate               = fread(fid,1,'float32');   % [counts/sec]   total_random = random_rate*frame_duration */
sh.singles_rate              = fread(fid,1,'float32');   % [counts/sec]   average bucket singles rate */
sh.scatter_fraction          = fread(fid,1,'float32');
sh.cti_fill                  = fread(fid,87+49-4*2,'int16'); % 20020627 btc (ray forgot to read this).  20021029 rfm2 change 48 to 49
%sh.cti_fill                  = fread(fid,87+49,'int16'); % 20020627 btc (ray forgot to read this).  20021029 rfm2 change 48 to 49
sz = [sh.x_dimension sh.y_dimension sh.z_dimension];
return


function [sh, sz] = readSubheaderAttenuation(fid, dirtable)
% fid = file identifier (of open file).  On input file position must correspond
%   to start of subheader.  On output, file will be positioned for reading pixel data.
% dirtable = directory record
% sh = subheader
% sz = [nx, ny, nz] = size of matrix that follows this subheader

% atn file
sh.data_type                 = fread(fid,1,'int16');
sh.num_dimensions            = fread(fid,1,'int16');
sh.num_r_elements            = fread(fid,1,'int16');
sh.num_angles                = fread(fid,1,'int16');
sh.num_z_elements            = fread(fid,1,'int16');
sh.corrections_applied       = fread(fid,1,'int16');
sh.ring_difference           = fread(fid,1,'int16');
pixel_resolutions            = fread(fid,4,'float32');
sh.x_resolution              = pixel_resolutions(1);
sh.y_resolution              = pixel_resolutions(2);
sh.z_resolution              = pixel_resolutions(3);
sh.w_resolution              = pixel_resolutions(4);
sh.scale_factor              = fread(fid,1,'float32');
pixel_offsets                = fread(fid,2,'float32');
sh.x_offset                  = pixel_offsets(1);
sh.y_offset                  = pixel_offsets(2);
radii                        = fread(fid,2,'float32');
sh.x_radius                  = radii(1);
sh.y_radius                  = radii(2);
sh.tilt_angle                = fread(fid,1,'float32');
sh.attenuation_coeff         = fread(fid,1,'float32');
sh.attenuation_min           = fread(fid,1,'float32');
sh.attenuation_max           = fread(fid,1,'float32');
sh.skull_thickness           = fread(fid,1,'float32');
sh.num_additional_atten_coeff= fread(fid,1,'int16');
sh.additional_atten_coeff    = fread(fid,8,'float32');
sh.edge_finding_threshold    = fread(fid,1,'float32');
sh.storage_order             = fread(fid,1,'int16');
sh.span                      = fread(fid,1,'int16');
sh.z_elements                = fread(fid,64,'int16');
sh.fill                      = fread(fid,86+50,'int16');

switch sh.data_type
    case 5 % IEEE float (32 bit)
        sz = [sh.num_z_elements sh.num_angles (dirtable(3)-dirtable(2))*512/sh.num_z_elements/sh.num_angles/4];
    case 6 % SUN int16
        sz = [sh.num_z_elements sh.num_angles (dirtable(3)-dirtable(2))*512/sh.num_z_elements/sh.num_angles/2];
    otherwise
        warning('readECAT7: unrecognized data type');
end

return
