# Captain of Industry Recipe Parser

## Download

The latest editions of the output files are available for download in the [output folder](https://github.com/brct-james/captain-of-industry-recipe-parser/tree/main/output). There is currently no automation to keep these up to date, so you may need to run the script yourself if a new game version is released.

## Run Yourself

- Decompile game .dlls with ILSpy

- - Place .cs files in `./decompiled` in their respective directories e.g. `./decompiled/Mafi.Base.Prototypes.Machines/*.cs`

- - Place the Translations folder in decompiled as well e.g. `./decompiled/Translations/*.po`

- Install requirements.txt

- Run script `clear; python3 run.py`

- Check `./output` for TSVs

## TODO

- Improve comments, DRYness/atomization

- Expand id/translation map implementation for more than just Ids.Products

- Pull `OilDistillationData.DURATION` from the referenced class automatically rather than hard-coding

- Add custom logic for the weird files currently in the `files_to_skip` list

- Add electricity consumption

- Add building costs

- Look into multi-language export using translation files (`Chemical plant II` maps to `ChemicalPlant2__name`)

- Lookup `multiplier` for `void registerElectronics` / `registerCp` in `AssemblyData.cs` (affects input/output qtys) instead of hard-coding