import re
from pathlib import Path

def gen_ents(file):
    pin = Path('Assets') / 'Levels' / file / '.agl'
    pout = Path('Assets') / 'ReferenceDicts' / 'GameObjects' / file / '.agd'
    if pout.is_file():
        print(f'ERROR: File {pout} already exists')
    elif not pin.is_file():
        print(f'ERROR: File {pin} does not exist')
    else:
        with (
            open(pin, 'r', newline='') as fin,
            open(pout, 'w', newline='') as fout,
        ):
            values = sorted(list(set(re.split(r'[\s,]+', fin.read()))))

            fout.write('{\n')
            for i, value in enumerate(values):
                if value is None or value == '':
                    continue
                output = f'  "{value}' + '": {\n    "type": "",\n    "data": {\n      \n    }\n  }' + f'{(',' if i < len(values) - 1 else '')}\n'
                fout.write(output)
            fout.write('}')
            print(f'File {pout} created')

gen_ents('level3')
