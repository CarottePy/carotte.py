# carotte.py

### Usage

Print the netlist to the standard output:

    python carotte.py examples/nadder.py

(replace `examples/nadder.py` with your own circuit definition!)

Write the netlist to a file:

    python carotte.py -o nadder.net examples/nadder.py

Read the help!

    python carotte.py -h

### Tutorial

A tutorial is available in the 'tutorial' folder. Read the tutorial python files.

### Advanced quirks

carotte.py optionally supports ribbon logic operations (e.g. binary operations on values with bus size > 1).
Call `allow_ribbon_logic_operations(True)` to enable this feature.

### License

Most of this project is distributed under Creative Commons Zero v1.0 Universal (CC0-1.0). See `LICENSE` file.
`assignhooks` is distributed under MIT License (MIT).
