import argparse
import hashlib
import os
import hmac
import subprocess
import yaml
import crc32c


class ImageMetadata:
    """ Class holding Image Metadata before building binary"""

    def __init__(self):
        self.crc = 0
        self.completion_status = 1
        self.hmac_signature = None
        self.length = 0
        self.file_name = ""

    def print(self):
        """ Print current State of Image"""
        print(f"    Filename:           {self.file_name}")
        print(f"    CRC:                {hex(self.crc)} dec: {self.crc}")
        print(f"    Completion Status:  {self.completion_status}")
        print(f"    HMAC Signature:     {self.hmac_signature.hex()}")
        print(f"    Length:             {self.length}")


class GlobalImageMetadata:
    """ Class holding Metadata before building binary """

    def __init__(self):
        self.hmac_key_file = None
        self.images: list(ImageMetadata) = []

    def print(self):
        """
        Print current state of Metadata
        """
        print("<<Global Image Metadata>>")
        print(f"    HMAC Keyfile: {self.hmac_key_file}")
        for index, image in enumerate(self.images):
            print(f"<<Image {index} Metadata>>")
            image.print()


def calculate_crc32c(image_file):
    """
    Calculate the Castagnoli CRC32 of the given file
    """
    with open(image_file, "rb") as file:
        checksum = crc32c.crc32c(file.read())
        return checksum


def get_length(file_name):
    """ Get Length of a file"""
    return os.path.getsize(file_name)


def calculate_hmac_signature(image_file, key_file):
    """
    Calculate HMAC Signature from image file
    """
    with open(key_file, 'rb') as key:
        with open(image_file, 'rb') as image:
            signature = hmac.new(key.read(), image.read(), hashlib.sha256)
            return signature.digest()


def extract_image_metadata(global_metadata: GlobalImageMetadata, image_file, key_file):
    """
    Extract all metadata from images and key files.
    """
    global_metadata.hmac_key_file = key_file
    image_meta = ImageMetadata()
    image_meta.crc = calculate_crc32c(image_file)
    image_meta.length = get_length(image_file)
    image_meta.hmac_signature = calculate_hmac_signature(image_file, key_file)
    image_meta.file_name = image_file
    global_metadata.images.append(image_meta)


def create_output_binary(bootloader_file, output_file, config):
    """
    Create the output_file starting with the bootloader
    """
    length = get_length(bootloader_file)
    if length > config["bootloader_size"]:
        raise Exception(
            f"Bootloader is too big. Has {length} but only {config['bootloader_size']} allowed."
            "Check linkerfile")

    print(
        f"DD: Creating target binary {output_file}, based on bootloader:{bootloader_file}")
    cmd = ["dd", "conv=notrunc",  f"if={bootloader_file}", f"of={output_file}",
           "bs=1", f"seek={0}", "status=progress"]

    with subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
            close_fds=True, universal_newlines=True) as process:
        print(process.stdout.read())


def append_images_to_binary(images, output_file, config):
    """
    Append all images to their expected locaiton in the output_file
    """
    for index, image_file in enumerate(images):
        length = get_length(image_file)
        if length > config["max_image_size"]:
            print("Files should already be objcopied to binary!")
            raise Exception(
                f"Image {image_file} wit index {index} has {length} bytes,"
                f"but only {config['max_image_size']} fit in Slot")

        offset = config["image_begin_addresses"][index]
        print(
            f"DD: Appending to {output_file}, based on image {image_file} with index {index}")
        cmd = ["dd", "conv=notrunc",  f"if={image_file}", f"of={output_file}",
               "bs=1", f"seek={offset}", "status=progress"]

        with subprocess.Popen(
                cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                close_fds=True, universal_newlines=True) as process:
            print(process.stdout.read())


def write_hmac_key(output_file, key_file, config):
    """
    Put the given HMAC Key in the metadata of the given file
    """
    with open(output_file, 'rb+') as file:
        with open(key_file, 'rb') as key:
            file.seek(config["hmac_key_offset"])
            file.write(key.read())


def write_crc(output_file, crc, index, config):
    """
    Put the given CRC in the metadata of the given file to the given imageIndex
    """
    offset = config["first_crc_offset"] + config["size_of_metadata"] * index
    with open(output_file, 'rb+') as file:
        file.seek(offset)
        file.write(crc.to_bytes(4, config["byteorder"]))


def write_length(output_file, length, index, config):
    """
    Put the given Length in the metadata of the given file to the given imageIndex
    """
    offset = config["first_length_offset"] + config["size_of_metadata"] * index

    with open(output_file, 'rb+') as file:
        file.seek(offset)
        file.write(length.to_bytes(4, byteorder=config["byteorder"]))


def write_completion_status(output_file, completion_status, index, config):
    """
    Put the given Completion Status in the metadata of the given file to the given imageIndex
    """
    offset = config["first_completion_status_offset"] + \
        config["size_of_metadata"] * index

    with open(output_file, 'rb+') as file:
        file.seek(offset)
        file.write((completion_status).to_bytes(
            2, byteorder=config["byteorder"]))


def write_hmac_signature(output_file, hmac_signature, index, config):
    """
    Put the given HMAC Signature in the metadata of the given file to the given imageIndex
    """
    offset = config["first_hmac_offset"] + \
        config["size_of_metadata"] * index
    with open(output_file, 'rb+') as file:
        file.seek(offset)
        file.write(hmac_signature)


def fix_metadata(output_file, global_metadata: GlobalImageMetadata, config):
    """Write all required metadata to output_file"""
    write_hmac_key(output_file, global_metadata.hmac_key_file, config)
    for index, image in enumerate(global_metadata.images):
        write_crc(output_file, image.crc, index, config)
        write_length(output_file, image.length, index, config)
        write_completion_status(
            output_file, image.completion_status, index, config)
        write_hmac_signature(output_file, image.hmac_signature, index, config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Patch Binary')
    parser.add_argument("--images", nargs="+",
                        help='Path to image files. Can take multiple paths!')
    parser.add_argument('--bootloader', type=str,
                        help='path to bootloader file')
    parser.add_argument("--key_file", type=str,
                        help="path to the keyfile for hmac")
    parser.add_argument('--out', type=str, default="python-vorago.bin",
                        help='path to output image file')
    parser.add_argument('--config', type=str, default="va41620_dev_board",
                        help='name of the configuration. See config/xxx.yml for reference')

    args = parser.parse_args()

    # Select Configuration:
    with open(f"{os.path.dirname(__file__)}/config/{args.config}.yml") as config_file:
        configuration = yaml.load(config_file, Loader=yaml.FullLoader)

        # Construct Metadata
        global_image_metadata = GlobalImageMetadata()

        for image_file_name in args.images:
            extract_image_metadata(global_image_metadata,
                                   image_file_name, args.key_file)

        # Create Target Binary
        create_output_binary(args.bootloader, args.out, configuration)

        # Append Images to Binary
        append_images_to_binary(args.images, args.out, configuration)

        # Write Metadata
        fix_metadata(args.out, global_image_metadata, configuration)
        global_image_metadata.print()
        print(f"Created Binary: {os.getcwd()}/{args.out}")
