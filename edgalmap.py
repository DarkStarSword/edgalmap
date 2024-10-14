#!/usr/bin/env python3

import json
import gzip
import argparse
import collections
import sys, os
try:
    import winclipboard
except: # Occurs on WSL, fallback to calling clip.exe
    class winclipboard(object):
        def copy_text_simple(text):
            import subprocess
            subprocess.run("clip.exe", input=text)

# https://forums.frontier.co.uk/threads/warning-galaxy-map-operating-beyond-safety-limits.598751/
layers_map = {
        0: 11,
        'a': 11,
        1: 14,
        'b': 14,
        2: 17,
        'c': 17,
        3: 20,
        'd': 20,
        4: 23,
        'e': 23,
        5: 26,
        'f': 26,
        6: 29,
        'g': 29,
        7: 32,
        'h': 32,
}
def b(cube_layer, body_id):
    return body_id << layers_map[cube_layer]
def b_inv(cube_layer, system_id):
    return system_id & 2**(cube_layer+3)-1, system_id >> layers_map[cube_layer]

sector_lookup_file = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'PGSectorNames.json')
system_lookup_json = json.load(open(sector_lookup_file, 'r'), strict=False)
system_lookup_map = { x['Key']: x['PGN'] for x in system_lookup_json['ProceduralGeneratedSectorNames'] }
def system_lookup_key(sector_x, sector_y, sector_z):
    # "Key" seems rather unnecessary - could just take SectorX/Y/Z as a tuple and use that as the key...
    # Or better yet, the file could have been formatted to use a json map >_<
    # But anyway...
    return sector_x | sector_y<<7 | sector_z<<14
def lookup_sector_name(sector_key):
    return system_lookup_map[sector_key]
def lookup_sector_pos(sector_name):
    sector_lookup_map = { x['PGN'].strip('\t'): (x['Position']['SectorX'], x['Position']['SectorY'], x['Position']['SectorZ']) for x in system_lookup_json['ProceduralGeneratedSectorNames'] }
    return sector_lookup_map[sector_name]

named_systems = json.load(gzip.open('NamedSystems.json.gz'))
named_systems_dupe_counts = collections.Counter([k.lower() for k in named_systems.keys()])
named_systems_dupe_counts += collections.Counter({k.lower(): len(v) for k,v in named_systems.items() if isinstance(v, list)})
#print(named_systems_dupe_counts.most_common(500))

def s_by_name(system_name, body_id):
    named_system_count = named_systems_dupe_counts[system_name.lower()]
    if named_system_count > 1:
        print('NOTICE: There are multiple systems with this name, try looking up by SystemID instead:')
        for named_system_name, named_system_id in named_systems.items():
            if named_system_name.lower() == system_name.lower():
                if isinstance(named_system_id, list):
                    for named_system_id_ in named_system_id:
                        print('"%s": %i' % (named_system_name, named_system_id_))
                else:
                    print('"%s": %i' % (named_system_name, named_system_id))
        return
    elif named_system_count == 1:
        for named_system_name, named_system_id in named_systems.items():
            if named_system_name.lower() == system_name.lower():
                return s(named_system_id, body_id)
    prefix, _, suffix = system_name.rpartition(' ')
    if suffix == system_name or suffix[0].lower() not in 'abcdefgh':
        print('Malformed system name:', suffix)
        return
    cube_layer = ord(suffix[0].lower()) - ord('a')
    if suffix.find('-') == -1:
        suffix = '{}0-{}'.format(suffix[0], suffix[1:])
        fixed_system_name = '{} {}'.format(system_name.rpartition(' ')[0], suffix)
        print('NOTE: Added implicit boxel zero remainder to system name: {}'.format(fixed_system_name))
        system_name = fixed_system_name
    boxel_remainder, _, system_id = suffix[1:].rpartition('-')
    if not system_id.isnumeric():
        print('Malformed system ID:', suffix)
        return
    system_id_masked, body_id_a = b_inv(cube_layer, int(system_id))
    #print(cube_layer, system_id, system_id_masked, body_id_a)

    system_name = system_name[:-len(system_id)] + str((int(system_id) + b(cube_layer, body_id or 0)))
    system_name_a = '{}-{}'.format(system_name.rpartition('-')[0], system_id_masked)

    if body_id is not None and body_id_a:
        print("WARNING: Address already included BodyID %i, replacing with -b %i" % (body_id_a, body_id))
        system_name = '{}-{}'.format(system_name.rpartition('-')[0], system_id_masked + b(cube_layer, body_id))
    elif body_id is None:
        body_id = body_id_a

    if body_id_a:
        # Body ID was included in the address cryptically, and we are about to
        # send it to the clipboard cryptically... show the readable ID as well
        print("%s, Body %i" % (system_name_a, body_id))

    try:
        system_address = encode_system_address(prefix, cube_layer, int(boxel_remainder), system_id_masked)
        (system_address, body_addr) = calc_body_addr(system_address, body_id)
        print('System Address: %i' % system_address)
        print('Body Address: %i' % body_addr)
    except KeyError:
        # Probably a sector defined by XYZ + radius (e.g. Col 89) rather than
        # boxel that we can't look up in the PGSectorNames.json file
        print('Unable to calculate system address')

    winclipboard.copy_text_simple(system_name.encode('ascii'))
    print('Copied to clipboard: "%s"' % system_name)

def resolve_system_address(system_address, body_id=None):
    def get_bits(n):
        return system_address >> n, system_address & 2**n-1
    system_address, cube_layer = get_bits(3)
    boxel_bits = 7 - cube_layer
    #print('layer', cube_layer)
    #print('boxel_bits', boxel_bits)
    system_address, boxel_z    = get_bits(boxel_bits)
    system_address, sector_z   = get_bits(7)
    system_address, boxel_y    = get_bits(boxel_bits)
    system_address, sector_y   = get_bits(6)
    system_address, boxel_x    = get_bits(boxel_bits)
    system_address, sector_x   = get_bits(7)
    system_id_bits = 11 + cube_layer*3
    #print('system_id_bits', system_id_bits)
    system_address, system_id  = get_bits(system_id_bits)
    system_address, body_id_a  = get_bits(9)
    #print('sector', sector_x, sector_y, sector_z)
    #print('boxel', boxel_x, boxel_y, boxel_z)
    #print('system_id', system_id)
    #print('body_id', body_id_a)
    if body_id is not None and body_id_a:
        print("WARNING: Address already included BodyID %i, replacing with -b %i" % (body_id_a, body_id))
    elif body_id_a:
        body_id = body_id_a
    elif body_id is None:
        body_id = 0
    try:
        sector_key = system_lookup_key(sector_x, sector_y, sector_z)
        sector_name = lookup_sector_name(sector_key).strip('\t')
    except KeyError as e:
        print('Sector missing from PGSectorNames.json, please add an entry such as this with PGN filled out:')
        print('{"Key": %i ,"PGN":"","Position":{"SectorX": %d, "SectorY": %d, "SectorZ": %d}},' % ( \
            sector_key, sector_x, sector_y, sector_z
        ))
        return
    #print('sector', sector_name)
    boxel_key = boxel_x | boxel_y<<7 | boxel_z<<14
    def to_letter(n):
        return chr(ord('A') + n)
    boxel_letter_a  = to_letter(boxel_key  % 26)
    boxel_letter_b  = to_letter(boxel_key // 26  % 26)
    boxel_letter_c  = to_letter(boxel_key // 26 // 26  % 26)
    boxel_remainder = boxel_key // 26 // 26 // 26
    system_name = '%s %s%s-%s %s' % \
            (sector_name,
            boxel_letter_a,
            boxel_letter_b,
            boxel_letter_c,
            to_letter(cube_layer).lower())
    if (boxel_remainder):
        system_name += '%d-' % boxel_remainder
    body_search_string = '%s%s' % (system_name, system_id + b(cube_layer, body_id))
    system_name = '%s%s' % (system_name, system_id)
    return (system_name, body_search_string, body_id)

# NOTE: This function expects the final suffix to have already been decoded by
# the caller to reduce redundant code
def encode_system_address(prefix, cube_layer, boxel_remainder, system_id, body_id=0):
    sector_name, _, boxel_string = prefix.rpartition(' ')
    sector_x, sector_y, sector_z = lookup_sector_pos(sector_name)

    def from_letter(n):
        return ord(n) - ord('A')
    assert(len(boxel_string) == 4)
    boxel_key  = from_letter(boxel_string[0])
    boxel_key += from_letter(boxel_string[1]) * 26
    assert(boxel_string[2] == '-')
    boxel_key += from_letter(boxel_string[3]) * 26 * 26
    boxel_key += boxel_remainder * 26 * 26 * 26
    boxel_x = (boxel_key      ) & 0x7f
    boxel_y = (boxel_key >>  7) & 0x7f
    boxel_z = (boxel_key >> 14) & 0x7f
    assert(boxel_key == boxel_x | boxel_y<<7 | boxel_z<<14)
    #print('boxel', boxel_key, boxel_x, boxel_y, boxel_z)

    boxel_bits = 7 - cube_layer
    system_id_bits = 11 + cube_layer*3
    system_address = 0
    def put_bits(n, val):
        assert(val & ~(2**n-1) == 0)
        return system_address << n | val
    system_address = put_bits(9, body_id)
    system_address = put_bits(system_id_bits, system_id)
    system_address = put_bits(7, sector_x)
    system_address = put_bits(boxel_bits, boxel_x)
    system_address = put_bits(6, sector_y)
    system_address = put_bits(boxel_bits, boxel_y)
    system_address = put_bits(7, sector_z)
    system_address = put_bits(boxel_bits, boxel_z)
    system_address = put_bits(3, cube_layer)
    return system_address

def calc_body_addr(system_addr, body_id):
    system_addr_masked = system_addr & (2**(64-9)-1)
    body_addr = (body_id << (64-9)) | system_addr_masked
    system_addr = system_addr & (2**(64-9)-1)
    return (system_addr_masked, body_addr)

def s(system_address, body_id=None):
    if isinstance(system_address, str):
        return s_by_name(system_address, body_id)

    (system_name, body_search_string, body_id_a) = resolve_system_address(system_address, body_id)
    (system_address, body_addr) = calc_body_addr(system_address, body_id_a)

    if body_id_a:
        # Body ID was included in the address cryptically, and we are about to
        # send it to the clipboard cryptically... show the readable ID as well
        print("%s, Body %i" % (system_name, body_id_a))
    winclipboard.copy_text_simple(body_search_string.encode('ascii'))
    print('System Address: %i' % system_address)
    print('Body Address: %i' % body_addr)
    print('Copied to clipboard: "%s"' % body_search_string)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Warning: Galaxy Map Operating Beyond Safety Limits!")
    parser.add_argument('-b', '--body-id', type=int, default=None, help='BodyID to target')
    parser.add_argument('system', nargs='+', help='System name (generic names only) or numeric SystemAddress from journal (required for named systems)')
    args = parser.parse_args()
    system = ' '.join(args.system)
    if system.isnumeric():
        system = int(system)
    s(system, args.body_id)
