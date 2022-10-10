# D2R-Multibox
A helper utility to streamline launching of D2R multibox.

NOTE: This only works on Windows.

## Background

In order to support multi-boxing (i.e. multiple instances of D2R running simultaneously), you need to kill the following `\Sessions\3\BaseNamedObjects\DiabloII Check For Other Instances`.

Many folks are doing this manually using tools like Process Explorer:

![Image of Process Explorer](https://i.imgur.com/sAhmhLD.png)

This script looks to automate that process, by iterating through all the processes and closing this handle.

## Dependencies

- Python 3
- The following python modules:

```
python -m pip install pywin32
python -m pip install ctypes
```

## Running the script

To run the script, simply run:

```
python D2R.py
```
