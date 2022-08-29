# bareboot-initial-metadata

When using [Bareboot](https://github.com/ThisIsPatrickM/bareboot) bootloader it expects Metadata, Bootloader and Application Images to be in a specific location.

This projects helps creating configurations and using them to create binaries of the bootloader and images to flash. 

## Generate Platform Config

Loads every yml file in `platform_description/` to generate a configuration under `config/...`.
To add a new configuration copy `platform_description/template.yml` and adjust the values as desired.
The generated configurations can be used by `initial_metadata.py`

Example: `python3 generate_platform_config.py`

## Initial Metadata

Takes multiple application image files, one bootloader file, a hmac key file and a configuration created with `generate_platform_config.py` to create one binary, that can be flashed onto an embedded system. It calculate all metadata and put metadata, bootloader and images to the expected location.

Example: `python3 initial_metadata.py --images example.bin --bootloader bootloader.bin --key_file my.key --config va41620`
