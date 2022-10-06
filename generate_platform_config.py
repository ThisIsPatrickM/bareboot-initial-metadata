import os
import yaml

PLATFORM_DESCRIPTION_PATH = "platform_description"
GENERRATED_CONFIG_PATH = "config"


IMAGE_METADATA_SIZES_TEMPLATE = {"version": 4,
                                 "crc": 4,
                                 "bootcounter": 4,
                                 "lastSuccessStatus": 4,
                                 "imageBegin": "pointer_size",
                                 "length": 4,
                                 "completionStatus": 2,
                                 "protectionStatus": 2,
                                 "hmacSignature": "hmac_signature_size"}

GLOBAL_METADATA_SIZE_TEMPLATE = {"globalBootCounter": 4,
                                 "prefferedImage": "size_t_size",
                                 "currentImage": "size_t_size",
                                 "hmacKey1": "hmac_key_size",
                                 "hmacKey2": "hmac_key_size",
                                 "hmacKey3": "hmac_key_size",
                                 "imageMetadata": 0
                                 }


def add_warning_to_file(file):
    """Prints automatically generated warning to file"""
    file.write("# Automatically generated. Don't edit manually\n")


def save_config(config):
    """Save config as yml file"""
    with open(f"{GENERRATED_CONFIG_PATH}/{config['name']}.yml", 'w') as file:
        add_warning_to_file(file)
        yaml.dump(config, file)


def generate_image_begin_addresses(platform, config):
    """Calculate addresses where images begin and save to config"""
    config["image_begin_addresses"] = []
    for i in range(0, platform["number_of_images"]):
        config["image_begin_addresses"].append(
            platform["bootloader_size"] + i * platform["max_image_size"])


def generate_size_of_metadata(platform, config) -> dict:
    """Calculates the size of metadata information for further calculation"""
    metadata_sizes = {}
    for key, value in IMAGE_METADATA_SIZES_TEMPLATE.items():
        if isinstance(value, int):
            metadata_sizes[key] = value
        else:
            metadata_sizes[key] = platform[value]
    size = 0
    for value in metadata_sizes.values():
        size += value
    config["size_of_metadata"] = size
    return metadata_sizes


def generate_global_metadata_sizes(platform) -> dict:
    """Calculates the size of global metadata information for further calculation"""
    global_metadata_sizes = {}
    for key, value in GLOBAL_METADATA_SIZE_TEMPLATE.items():
        if isinstance(value, int):
            global_metadata_sizes[key] = value
        else:
            global_metadata_sizes[key] = platform[value]
    return global_metadata_sizes


def get_offset_of(prop, platform, metadata_sizes: dict, global_metadata_sizes: dict):
    """Calculates the offset of property, depending on platform and previously
    calculates metadata sizes"""
    offset = platform["metadata_label_address"]
    for key, value in global_metadata_sizes.items():
        if key == prop:
            return offset
        offset += value

    for key, value in metadata_sizes.items():
        if key == prop:
            return offset
        offset += value
    return 0


def generate_offsets(platform, config, metadata_sizes: dict, global_metadata_sizes: dict):
    """Saves required offsets into config"""
    config["hmac_key_offset"] = get_offset_of(
        "hmacKey1", platform, metadata_sizes, global_metadata_sizes)
    config["first_image_metadata_offset"] = get_offset_of(
        "imageMetadata", platform, metadata_sizes, global_metadata_sizes)
    config["first_crc_offset"] = get_offset_of(
        "crc", platform, metadata_sizes, global_metadata_sizes)
    config["first_length_offset"] = get_offset_of(
        "length", platform, metadata_sizes, global_metadata_sizes)
    config["first_completion_status_offset"] = get_offset_of(
        "completionStatus", platform, metadata_sizes, global_metadata_sizes)
    config["first_hmac_offset"] = get_offset_of(
        "hmacSignature", platform, metadata_sizes, global_metadata_sizes)


def generate_config(platform_filename):
    """Creates a config file, based on the given platform_file"""
    with open(f"{PLATFORM_DESCRIPTION_PATH}/{platform_filename}") as file:
        platform = yaml.load(file, Loader=yaml.FullLoader)
        config = {}
        config["name"] = platform["name"]
        generate_image_begin_addresses(platform, config)
        metadata_sizes = generate_size_of_metadata(platform, config)
        global_metadata_sizes = generate_global_metadata_sizes(
            platform)
        generate_offsets(platform, config, metadata_sizes,
                         global_metadata_sizes)
        # Copy required fields
        config["bootloader_size"] = platform["bootloader_size"]
        config["byteorder"] = platform["byteorder"]
        config["max_image_size"] = platform["max_image_size"]
        print(config)
        save_config(config)


if __name__ == "__main__":
    platform_files = list(filter(lambda name: name != "template.yml",
                                 os.listdir(PLATFORM_DESCRIPTION_PATH)))
    for platform_file in platform_files:
        generate_config(platform_file)
    print("Done")
