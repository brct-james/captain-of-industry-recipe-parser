# Captain of Industry Recipe Parser

## Run

- Decompile game .dlls with ILSpy

- - Place .cs files in `./decompiled` in their respective directories (e.g. `./decompiled/Mafi.Base.Prototypes.Machines/*.cs`)

- Install requirements.txt

- Run script `clear; python3 parse_decompiled_machines.py`

- Check `./output` for CSVs