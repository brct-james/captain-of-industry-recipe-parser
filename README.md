# Captain of Industry Recipe Parser

## Download

The latest editions of the output files are available for download in the [output folder](https://github.com/brct-james/captain-of-industry-recipe-parser/tree/main/output). There is currently no automation to keep these up to date, so you may need to run the script yourself if a new game version is released.

## Run Yourself

- Decompile game .dlls with ILSpy

- - Place .cs files in `./decompiled` in their respective directories (e.g. `./decompiled/Mafi.Base.Prototypes.Machines/*.cs`)

- Install requirements.txt

- Run script `clear; python3 parse_decompiled_machines.py`

- Check `./output` for TSVs

## TODO

- Improve comments, DRYness/atomization

- Seems like I can use the translation .po files to get the readable product name by manipulating `Ids.Products.CopperScrap` into `Product_CopperScrap_name` then looking it up in the tranlation file
- - Could support multi-language export if I can also lookup the translations for the machines (and recipe names? or are these unnecessary) it seems `Chemical plant II` maps to `ChemicalPlant2__name`
- - Looks like I will have to walk these through `Mafi.Base/Ids.cs` to get the id used in the translation string. The only one I found that can't be directly converted is `Ids.Products.SteamLo` which is actually `Product_SteamLP_name` in the strs

- Write lookups for input and output qtys cause apparently we're using vars there too...

- Pull `OilDistillationData.DURATION` from the referenced class automatically rather than hard-coding

- Support for arthimetic in fields (e.g. `3 * duration` and `2 * OilDistillationData.DURATION`)

- Add custom logic for the weird files currently in the `files_to_skip` list

- Add electricity consumption

- Add building costs