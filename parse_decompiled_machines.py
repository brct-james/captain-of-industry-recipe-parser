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
        print(match)
        duration_id = match[0]
        duration_time = match[1]
        if duration_time.endswith('.Seconds()'):
            duration_time = duration_time[:-10]
        duration_dict[duration_id] = duration_time
    print(f'{duration_dict}')
    return duration_dict

def construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs):
    recipes_dict.setdefault('identifier', []).append(identifier)
    recipes_dict.setdefault('name', []).append(name)
    recipes_dict.setdefault('machine', []).append(machine)
    recipes_dict.setdefault('duration', []).append(duration)
    recipes_dict.setdefault('input1name', []).append(inputs[0][1])
    recipes_dict.setdefault('input1qty', []).append(inputs[0][0])
    recipes_dict.setdefault('input2name', []).append(inputs[1][1])
    recipes_dict.setdefault('input2qty', []).append(inputs[1][0])
    recipes_dict.setdefault('input3name', []).append(inputs[2][1])
    recipes_dict.setdefault('input3qty', []).append(inputs[2][0])
    recipes_dict.setdefault('input4name', []).append(inputs[3][1])
    recipes_dict.setdefault('input4qty', []).append(inputs[3][0])
    recipes_dict.setdefault('input5name', []).append(inputs[4][1])
    recipes_dict.setdefault('input5qty', []).append(inputs[4][0])
    recipes_dict.setdefault('input6name', []).append(inputs[5][1])
    recipes_dict.setdefault('input6qty', []).append(inputs[5][0])
    recipes_dict.setdefault('output1name', []).append(outputs[0][1])
    recipes_dict.setdefault('output1qty', []).append(outputs[0][0])
    recipes_dict.setdefault('output2name', []).append(outputs[1][1])
    recipes_dict.setdefault('output2qty', []).append(outputs[1][0])
    recipes_dict.setdefault('output3name', []).append(outputs[2][1])
    recipes_dict.setdefault('output3qty', []).append(outputs[2][0])
    recipes_dict.setdefault('output4name', []).append(outputs[3][1])
    recipes_dict.setdefault('output4qty', []).append(outputs[3][0])
    recipes_dict.setdefault('output5name', []).append(outputs[4][1])
    recipes_dict.setdefault('output5qty', []).append(outputs[4][0])
    recipes_dict.setdefault('output6name', []).append(outputs[5][1])
    recipes_dict.setdefault('output6qty', []).append(outputs[5][0])
    return recipes_dict

def build_recipes_dict(file, machine_dict, duration_dict):
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
                recipes_dict = construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs)
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
            recipes_dict = construct_recipes_dict(recipes_dict, identifier, name, machine, duration, inputs, outputs)
        
    return recipes_dict

def parse_file(filepath):
    with open(filepath, 'r') as file_object:
        print('Read File')
        file = file_object.read()
        print('Build Machine Dict and MCM')
        machine_dict, machine_cost_map = build_machine_dict_and_mcm(file)
        print('Build Duration Dict')
        duration_dict = build_duration_dict(file)
        print('Build Recipes Dict')
        recipes_dict = build_recipes_dict(file, machine_dict, duration_dict)
    return (recipes_dict, machine_cost_map)

def main():
    # files = ['MetalCastersData.cs', 'FurnacesData.cs']
    files = []
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

        recipe_entries, mcm = parse_file(filepath)
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
    df.to_csv('output/decompiled_machine_recipes.csv', sep='\t', index=False)
    mcm_df.to_csv('output/decompiled_machine_cost_map.csv', sep='\t', header=False)
    print("\n-- Done --")
if __name__ == '__main__':
    main()