Calculates Elite Dangerous galaxy map addresses that target a specific body within a system.

Based on the technique described by CMDR Pyroboros:
https://forums.frontier.co.uk/threads/warning-galaxy-map-operating-beyond-safety-limits.598751/

Examples, looking up Sol by the SystemAddress from the player journal:

    ./edgalmap.py 10477373803
    Copied to clipboard: "Wregoe AC-D d12-0"

Looking up address of the HyperbolicOrbiter of the Thargoid Anomaly at confirmed waypoint 1:

    ./edgalmap.py Oochorrs UF-J c11-0 --body-id 17
    Copied to clipboard: "Oochorrs UF-J c11-2228224"

Looking up address of the HyperbolicOrbiter at predicted waypoint 4, system "HD 38291" body 17 by SystemAddress:

    ./edgalmap.py 1327473756 -b 17
    Copied to clipboard: "Oochorrs GR-V e2-142606336"

Looking up address of the HyperbolicOrbiter at predicted waypoint 12:

    ./edgalmap.py Col 69 Sector LM-U c3-1 -b 28
    Copied to clipboard: "Col 69 Sector LM-U c3-3670017"

Iterate over possibly hidden bodies in the current system (FSS scan everything first, note that this won't search through any gaps in the BodyIDs):

    ./find_bodies.sh
    Current system: Col 69 Sector WL-Q b20-0
    System Address: 677127660481
    Highest bodyID: 8
    
    ./edgalmap.py Col 69 Sector WL-Q b20-0 -b 9
    Copied to clipboard: "Col 69 Sector WL-Q b20-147456"
    
    Press enter to continue to next body, Ctrl+C to abort...
    
    ./edgalmap.py Col 69 Sector WL-Q b20-0 -b 10
    Copied to clipboard: "Col 69 Sector WL-Q b20-163840"
    
    Press enter to continue to next body, Ctrl+C to abort...
