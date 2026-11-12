# Keep lazy data lazy when a Variable is copied

## What to change
`Variable._replace` loads lazily-backed data into memory when it builds the new Variable.
It should pass the underlying data through without loading it.

## Where
`xarray/core/variable.py`, `Variable._replace`

## Details
None stated.
