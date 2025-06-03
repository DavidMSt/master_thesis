from intelhex import IntelHex

FLASH_START = 0x08000000
FLASH_END = 0x08200000  # Exclusive upper bound


def cropHex(file, start=FLASH_START, end=FLASH_END):
    ih = IntelHex(file)
    all_addresses = list(ih.addresses())
    removed = 0
    for addr in all_addresses:
        if addr < start or addr >= end:
            del ih[addr]
            removed += 1

    print(f"✅ Removed {removed} bytes outside of 0x{start:08X} - 0x{end - 1:08X}")
    ih.write_hex_file(file)


if __name__ == '__main__':
    cropHex('/Users/lehmann/Desktop/bilbo.hex')
