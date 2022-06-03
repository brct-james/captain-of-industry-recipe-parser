import re
import pandas as pd
from os import walk
import sys

# define regular expressions
rx_dict = {
    'recipe_builder': re.compile(r'registrator.RecipeProtoBuilder.Start(.*[^;]*)'),
    'machine_builder': re.compile(r'\tMachineProto (.*[^;]*)'),
    'machine_proto_builder': re.compile(r'registrator.MachineProtoBuilder.Start(.*[^;]*)'),
    'duration_definition': re.compile(r'\tDuration duration[0-9]?[^;]*'),
    'duration_def_ex1': re.compile(r'\t(DURATION) = (.*[^\t]);'),

    'ids_products': re.compile(r'static Products\(\)\n\t\t{\n([^}]*)'),
    'ids_core_products': re.compile(r'static Products\(\)\n\t\t{\n([^}]*)'),
    'translation_map': re.compile(r'msgid "(.*)"\nmsgstr "(.*)"'),
}

def build_machine_dict_and_mcm(file):
    # first find machine and duration definitions
    machine_matches = re.findall(rx_dict['machine_builder'], file)
    machine_matches.extend(re.findall(rx_dict['machine_proto_builder'], file))
    # print(len(machine_matches))
    machine_dict = {}
    machine_cost_map = {}
    for match in machine_matches:
        # print('')
        # print(match)
        if ' = ' in match:
            machine_split = match.split(' = ')
            # print(machine_split)
            machine_id = machine_split[0]
            machine_info = machine_split[1]

            # print(f'\nfirst machine info: {machine_info}\n')
            # if machine_info not start with registrator.MachineProtoBuilder.Start
            # lookup the object that machine_info starts with
            if not machine_info.startswith("registrator.MachineProtoBuilder.Start"):
                new_rx = machine_info.split('.')[0] + ' (.*[^;]*)'
                # print(f'\nnew_rx: {new_rx}\n')
                new_info = re.search(new_rx, file)
                if new_info:
                    machine_info = new_info.group(0).split(" = registrator.MachineProtoBuilder.")[1]
            else:
                # remove registrator.MachineProtoBuilder. from start
                machine_info = machine_info[32:]
            # print(f'\nmachine_info: {machine_info}\n')

            sanitized = re.sub(r'[\t\n\r]', '', machine_info) # remove non-space whitespace
            if sanitized.endswith('.BuildAndAdd()'):
                sanitized = sanitized[:-14] # remove .BuildAndAdd()

            operations = sanitized.replace(').', ')).').split(').') # split on .
            # print(*operations, sep="\n")
            
            machine_name = ""
            for op in operations:
                if op.startswith('Start'):
                    machine_name = op[6:-1].split(', ')[0][1:-1]
                    machine_dict[machine_id] = machine_name
                elif op.startswith('SetCost'):
                    machine_cost_id = op[8:-1]
                    machine_cost_map[machine_name] = [machine_cost_id]
        else:
            sanitized = 'Start' + re.sub(r'[\t\n\r]', '', match) # remove non-space whitespace
            if sanitized.endswith('.BuildAndAdd()'):
                sanitized = sanitized[:-14] # remove .BuildAndAdd()

            operations = sanitized.replace(').', ')).').split(').') # split on .
            # print(*operations, sep="\n")

            machine_name = ""
            for op in operations:
                if op.startswith('Start'):
                    machine_name = op[6:-1].split(', ')[0][1:-1]
                    machine_id = op[6:-1].split(', ')[1]
                    machine_dict[machine_id] = machine_name
                    # print(f'machine_dict: {machine_dict} ')
                elif op.startswith('SetCost'):
                    machine_cost_id = op[8:-1]
                    machine_cost_map[machine_name] = [machine_cost_id]


        
    # print(machine_dict)
    # print(machine_cost_map)
    return (machine_dict, machine_cost_map)

def build_duration_dict(file):
    duration_matches = re.findall(rx_dict['duration_definition'], file)
    duration_dict = {}
    # print('')
    for match in duration_matches:
        # print(match)
        duration_split = match[10:].split(' = ')
        # print(duration_split)
        duration_id = duration_split[0]
        duration_time = duration_split[1]
        if duration_time.endswith('.Seconds()'):
            duration_time = duration_time[:-10]
        duration_dict[duration_id] = duration_time

    duration_matches_ex = re.findall(rx_dict['duration_def_ex1'], file)
    for match in duration_matches_ex:
        # print(match)
        duration_id = match[0]
        duration_time = match[1]
        if duration_time.endswith('.Seconds()'):
            duration_time = duration_time[:-10]
        duration_dict[duration_id] = duration_time
    # print(f'{duration_dict}')
    return duration_dict

def _lookup_io_name_id_translation(ioname, ids_dict, translations_dict):
    if ioname == '':
        return ioname
    if ioname in ids_dict:
        ioname = ids_dict[ioname]
        if ioname in translations_dict:
            ioname = translations_dict[ioname]
        else:
            print(f'Product name not in translations_dict: {ioname}')
    else:
        print(f'Product name not in ids_dict: {ioname}')
    return ioname

def construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs, ids_dict, translations_dict):
    recipes_dict.setdefault('identifier', []).append(identifier)
    recipes_dict.setdefault('name', []).append(name)
    recipes_dict.setdefault('machine', []).append(machine)
    recipes_dict.setdefault('duration', []).append(duration)
    for n in range(1, 6+1):
        input_name = _lookup_io_name_id_translation(inputs[n-1][1], ids_dict, translations_dict)
        input_qty = inputs[n-1][0]
        recipes_dict.setdefault(f'input{n}name', []).append(input_name)
        recipes_dict.setdefault(f'input{n}qty', []).append(input_qty)
    for n in range(1, 6+1):
        output_name = _lookup_io_name_id_translation(outputs[n-1][1], ids_dict, translations_dict)
        output_qty = outputs[n-1][0]
        recipes_dict.setdefault(f'output{n}name', []).append(output_name)
        recipes_dict.setdefault(f'output{n}qty', []).append(output_qty)
    return recipes_dict

def build_recipes_dict(file, machine_dict, duration_dict, ids_dict, translations_dict):
    # now search for recipes
    recipe_matches = re.findall(rx_dict['recipe_builder'], file)
    recipes_dict = {}
    for match in recipe_matches:
        # print('')
        sanitized = 'Start' + re.sub(r'[\t\n\r]', '', match) # remove non-space whitespace
        sanitized = sanitized[:-14] # remove .BuildAndAdd()

        operations = sanitized.replace(').', ')).').split(').') # split on .
        start_op = ''
        input_ops = []
        output_ops = []
        duration_op = ''
        for op in operations:
            if op.startswith('AddInput'):
                input_ops.append(op[9:-1])
            elif op.startswith('AddOutput'):
                output_ops.append(op[10:-1])
            elif op.startswith('Start'):
                start_op = op[6:-1]
            elif op.startswith('SetDuration'):
                if op.startswith('SetDurationSeconds'):
                    duration_op = op[19:-1]
                else:
                    duration_op = op[12:-1]
            else:
                # print(f'Unknown Operation: {op}')
                pass
        
        name = start_op.split(", ")[0][1:-1]
        # print(f'Name: {name}')
        inputs = [['','']] * 6
        for idx, inp in enumerate(input_ops):
            # print(inp)
            inp_split = inp.split(', ')
            # print(inp_split)
            inputs[idx] = inp_split[0:2]
        # print(f'Inputs: {inputs}')
        outputs = [['','']] * 6
        for idx, otp in enumerate(output_ops):
            # print(otp)
            otp_split = otp.split(', ')
            # print(otp_split)
            outputs[idx] = otp_split[0:2]
        # print(f'Outputs: {outputs}')
        identifier = start_op.split(", ")[1]
        # print(f'ID: {identifier}')
        if identifier in ['recipeId', 'id']:
            # is likely a void method, look up two lines for void register(.*)\(RecipeProto.ID
            # the (.*) is the method name, then look for it in the file to find the call
            # which will have args (identifier, machine, duration)
            # note multiple calls to the method will mean you need multiple recipe entries
            line_lookup = match.split('\n')[0]
            # print(line_lookup)
            split_line_file = file.splitlines()
            found_num = -1
            for num, line in enumerate(split_line_file, 1):
                if line_lookup in line:
                    # print('found at line:', num)
                    found_num = num
                    break
            target_line_num = found_num - 3 # sub 3, 2 to go up two lines, one more for idx discrepancies
            target_line = split_line_file[target_line_num]
            # print(f'{target_line_num}: {target_line}')
            method_name = target_line.replace('\t','').split('(RecipeProto.ID')[0][5:]
            # print(method_name)
            method_calls = re.findall(f'{method_name}(.*[^\t];)', file)
            for call in method_calls:
                # print(call)
                args = call[1:-2].split(", ")
                # print(args)
                identifier = args[0]
                machine = args[1]
                duration = args[2]
                if machine in machine_dict:
                    machine = machine_dict[machine]
                # print(f'Machine: {machine}')
                if duration in duration_dict:
                    duration = duration_dict[duration]
                elif duration.endswith('.Seconds()'):
                        duration = duration[:-10]
                # TODO: figure out how to pull this programmatically instead, incase values change in future
                elif duration == '2 * OilDistillationData.DURATION':
                    duration = '40'
                elif duration == 'OilDistillationData.DURATION':
                    duration = '20'
                elif duration == '3 * duration' and machine == 'Crusher':
                    duration = 20
                # print(f'Duration: {duration}')
                recipes_dict = construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs, ids_dict, translations_dict)
        else:
            machine = start_op.split(", ")[2]
            if machine in machine_dict:
                machine = machine_dict[machine]
            # print(f'Machine: {machine}')
            duration = duration_op
            # print(duration)
            # print(duration_dict)
            if duration in duration_dict:
                duration = duration_dict[duration]
            elif duration.endswith('.Seconds()'):
                duration = duration[:-10]
            # TODO: figure out how to pull this programmatically instead, incase values change in future
            elif duration == '2 * OilDistillationData.DURATION':
                duration = '40'
            elif duration == 'OilDistillationData.DURATION':
                duration = '20'
            elif duration == '3 * duration' and machine == 'Crusher':
                duration = 20
            # print(f'Duration: {duration}')
            recipes_dict = construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs, ids_dict, translations_dict)
        
    return recipes_dict

def parse_machine_prototypes(filepath, ids_dict, translations_dict):
    with open(filepath, 'r') as file_object:
        print('Read File')
        file = file_object.read()
        print('Build Machine Dict and MCM')
        machine_dict, machine_cost_map = build_machine_dict_and_mcm(file)
        print('Build Duration Dict')
        duration_dict = build_duration_dict(file)
        print('Build Recipes Dict')
        recipes_dict = build_recipes_dict(file, machine_dict, duration_dict, ids_dict, translations_dict)
    return (recipes_dict, machine_cost_map)

def _transform_id_match(match, matches):
    if ' = ' not in match or (' = new ' in match and '"' not in match) or 'new Proto.ID("Product_VirtualResource' in match:
        print(f'Skipping {match}')
        return []
    split = match.split(' = ')
    product_id = split[0]
    translation_id = split[1]
    result = []
    if translation_id.startswith('CreateId('):
        translation_id = translation_id[10:-2]
    elif translation_id.startswith('CreateVirtualId('):
        translation_id = 'Virtual_' + translation_id[17:-2]
    elif translation_id.startswith('new ProductProto.ID('):
        translation_id = translation_id[29:-2]
    elif translation_id.startswith('new Proto.ID('):
        translation_id = translation_id[22:-2]
    # add extra map for product_id if in IdsCore.Products
    elif translation_id.startswith('IdsCore.Products.'):
        core_product_id = translation_id[17:]
        for core_match in matches:
            if core_product_id in core_match and 'IdsCore.Products.' not in core_match:
                print(f'Found core product in matches: {core_product_id}: {core_match}')
                core_match_result = _transform_id_match(core_match, matches)
                translation_id = core_match_result[0][1]
                print(f'Adding extra core product to map: Ids.Products. {product_id} = {translation_id}')
                result.append((product_id, translation_id))
                product_id = core_product_id
                break
        if core_product_id != product_id:
            print(f'Could not find core product in matches: {core_product_id}: {matches}')
            sys.exit()
    result.append((product_id, translation_id))
    return result

def parse_ids(path_to_ids, path_to_core_ids):
    # TODO: expand to more than IDs.Products
    ids_dict = {}
    with open(path_to_ids, 'r') as file_object:
        print('Read IDs File')
        file = file_object.read()
        matches = re.findall(rx_dict['ids_products'], file)[0]
        with open(path_to_core_ids, 'r') as core_file_object:
            print('Read Core IDs File')
            core_file = core_file_object.read()
            matches += re.findall(rx_dict['ids_core_products'], core_file)[0]
        matches = re.sub(r'[\t\n\r]', '', matches)
        matches = matches.split(';')
        # print(*matches, sep='\n')
        print('Process Matches')
        for match in matches:
            pairs = _transform_id_match(match, matches)
            for pair in pairs:
                ids_dict['Ids.Products.' + pair[0]] = pair[1]
    return ids_dict

def parse_translations(path_to_translations):
    translations_dict = {}
    with open(path_to_translations, 'r') as file_object:
        print('Read translations file')
        file = file_object.read()
        matches = re.findall(rx_dict['translation_map'], file)
        # print(*matches, sep='\n')
        print('Process Matches')
        for match in matches:
            if match[0].startswith('Product_'):
                translation_id = match[0][8:-6]
                translation_msg = match[1]
                translations_dict[translation_id] = translation_msg
    # print(translations_dict['SteamLP'])
    return translations_dict

def main():
    # Get ID map from Mafi.Base/Ids.cs
    print('Processing IDs')
    ids_dict = parse_ids('decompiled/Mafi.Base/Ids.cs', 'decompiled/Mafi.Core/IdsCore.cs')
    print(f'Found {len(ids_dict)} entries\n')
    
    # Get translation map from Translations
    print('Processing Translations')
    translations_dict = parse_translations('decompiled/Translations/en.po')
    print(f'Found {len(translations_dict)} entries\n')

    # Check that all in ids_dict have entries in translation_dict
    print('Checking for ids without translations:\n')
    count = 0
    for key, value in ids_dict.items():
        if value not in translations_dict:
            count += 1
            msg = f'\t{key}: {value}'
            if key in translations_dict:
                msg += f' | Key Found in translations but value was: {translations_dict[key]}'
            print(msg)
    if count > 0:
        print('\n')
    print(f'Found {count} IDs missing translations\n')

    # Save maps as tsvs
    ids_df = pd.DataFrame.from_dict(data=ids_dict, orient='index')
    translations_df = pd.DataFrame.from_dict(data=translations_dict, orient='index')
    ids_df.to_csv('output/ids_map_df.tsv', sep='\t', header=False)
    translations_df.to_csv('output/translations_map_df.tsv', sep='\t', header=False)

    # Now process all machines
    print('Processing Machines')
    # files = ['MetalCastersData.cs', 'FurnacesData.cs']
    files = []
    print('Get Filepaths')
    for (dirpath, dirnames, filenames) in walk('decompiled/Mafi.Base.Prototypes.Machines'):
        # TODO: Microchips, Flares and other waste venters are weird, need to add custom logic
        files_to_skip = ['FlareData.cs', 'SmokeStackData.cs', 'MicrochipMakerData.cs', 'AnaerobicDigesterData.cs', 'BurnerData.cs', 'GeneralMixerData.cs', 'WellPumpsData.cs']
        for skip_file in files_to_skip:
            try:
                filenames.remove(skip_file)
            except:
                print(f"{skip_file} not found, skipping removal")
        files.extend(filenames)
        break;

    df = pd.DataFrame()
    mcm_dc = pd.DataFrame()
    df_size_sum = 0
    for path in files:
        print(f'\n-- {path} --')
        filepath = 'decompiled/Mafi.Base.Prototypes.Machines/' + path

        recipe_entries, mcm = parse_machine_prototypes(filepath, ids_dict, translations_dict)
        if len(recipe_entries) > 0:
            df_size_sum += len(recipe_entries['identifier'])
            recipe_entries['file'] = [path] * len(recipe_entries['identifier'])
        if len(df) < 1:
            # create df
            df = pd.DataFrame(data=recipe_entries)
            mcm_df = pd.DataFrame.from_dict(data=mcm, orient='index')
        else:
            # concat instead
            new_df = pd.DataFrame(data=recipe_entries)
            new_mcm_df = pd.DataFrame.from_dict(data=mcm, orient='index')

            df = pd.concat([df, new_df], ignore_index=True)
            mcm_df = pd.concat([mcm_df, new_mcm_df], ignore_index=False)

    print(f'\n{df.head(5)}')
    print(f'\nRecipe Dictionary DF Shape: {df.shape}')
    print(f'\n{mcm_df.head(5)}')
    print(f'\nMCM Dictionary DF Shape: {mcm_df.shape}')
    df.to_csv('output/decompiled_machine_recipes.tsv', sep='\t', index=False)
    mcm_df.to_csv('output/decompiled_machine_cost_map.tsv', sep='\t', header=False)
    print("\n-- Done --")
if __name__ == '__main__':
    main()