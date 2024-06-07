env = loadenv('variables.env');
ecat_file=env('WELL_BEHAVED_ECAT_FILE');
wustl_fbp_ecat=env('WUSTL_FBP_ECAT');
wustl_osem_ecat=env('WUSTL_OSEM_ECAT');

% convert the following ints to bytes and write them to a file
ints_to_write = [-32768, 32767]


% use the same format as the python version of this code
destination_file = 'matlab_sample_bytes.bytes'

% write all the ints as bytes to the file
fid = fopen(destination_file, 'w');
disp("writing ints_to_write to sample file");
disp(ints_to_write);
fwrite(fid, ints_to_write, 'int16', 'b');
%for i = 1:length(ints_to_write)
%    fwrite(fid, typecast(ints_to_write(i), 'int16'), 'int16', 'b');
%end
fclose(fid);

% read out the bytes as written to the sample file
fid = fopen('matlab_sample_bytes.bytes', 'r');
bytes = fread(fid);
disp("bytes written from matlab in matlab_sample_bytes.byte and read with fread (no arguments)");
disp(bytes);
fclose(fid);

% read in bytes from python, at least I have a good idea of what that is written as
fid = fopen('python_sample_bytes.bytes', 'r');
python_bytes = fread(fid);
disp("bytes written from python in python_sample_bytes.byte and read with fread (no arguments)");
disp(python_bytes);

various_data_types = {'int16=>int16', 'int16', 'uint16'};

disp("now we open the matlab file and read the bytes using multiple arguments for fread");

% read in the bytes as int16

calibration_factor = 0.7203709074867248;

for t = 1:length(various_data_types)
    % oddly enough varying the second argument to fread doesn't seem to change the output
    fid = fopen(destination_file, 'r', 'ieee-be');
    various_bytes = fread(fid, various_data_types{t});
    disp(['datatype used for reading in bytes: ', various_data_types{t}]);
    disp(various_bytes);
    disp(various_data_types{t});
    fclose(fid);
    
    % scale the data to see what happens
    scaled_bytes = calibration_factor * various_bytes
end
