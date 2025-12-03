import re
from os.path import isfile

def gen_ents(file):
    pin = 'C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Levels\\'
    pout = 'C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\ReferenceDicts\\GameObjects\\'
    if isfile(f'{pout}{file}.agd'):
        print(f'ERROR: File {pout}{file}.agd already exists')
    elif not isfile(f'{pin}{file}.agl'):
        print(f'ERROR: File {pin}{file}.agl does not exist')
    else:
        with (open(f'{pin}{file}.agl', 'r', newline='') as fin, open(f'{pout}{file}.agd', 'w', newline='') as fout):
            values = sorted(list(set(re.split(r'[\s,]+', fin.read()))))

            fout.write('{\n')
            for i, value in enumerate(values):
                if value is None or value == '':
                    continue
                output = f'  "{value}' + '": {\n    "type": "",\n    "data": {\n      \n    }\n  }' + f'{(',' if i < len(values) - 1 else '')}\n'
                fout.write(output)
            fout.write('}')
            print(f'File {pout}{file}.agd created')

gen_ents('level3')