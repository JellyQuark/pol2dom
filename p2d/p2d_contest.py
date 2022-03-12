import os
import requests
import shutil
import subprocess
import sys
import yaml
from argparse import ArgumentParser
from . import p2d_problem

OK_SYMBOL = u'\u2705'
NEUTRAL_SYMBOL = '  '
ERROR_SYMBOL = u'\u274C'

def find_latest_local_version(name, polygon):
    suffix = '$linux.zip'
    version = -1
    for f in os.listdir(polygon):
        prefix = name + '-'
        if f.startswith(name + '-') and f.endswith(suffix):
            maybe_version = f[len(prefix):-len(suffix)]
            if maybe_version.isdigit():
                version = max(version, int(f[len(prefix):-len(suffix)]))
    return version

def run_p2d_problem(name, old_version, letter, color, contest, polygon, domjudge):
    version = find_latest_local_version(name, polygon)
    if version == -1:
        print(ERROR_SYMBOL, name, ':', 'Not found.')
        return old_version
    assert(version != -1)
    if old_version > version:
        print(ERROR_SYMBOL, name, ':', 'The last used version is not present in the folder \'%s\'.' % polygon)
        return old_version
    assert(old_version <= version)
    
    if version == old_version:
        print(NEUTRAL_SYMBOL, name, ':', 'Already up to date, not modified.')
        return old_version

    args = p2d_problem.prepare_argument_parser().parse_args(
            ['--from', os.path.join(polygon, '%s-%s$linux.zip' % (name, version)),
            '--to', os.path.join(domjudge, '%s.zip' % letter),
            '--color', color,
            '--contest', contest,
            '--verbosity', 'warning',
            '--force'])

    try:
        p2d_problem.p2d_problem(args)
    except:
        print(ERROR_SYMBOL, name, ':', 'Error during the execution of p2d-problem.')
        return old_version

    print(OK_SYMBOL, name, ':', 'Converted into \'%s\'.'
          % (os.path.join(domjudge, letter + '.zip')))
    return version

def send_package_to_server(zip_file, problem_id, config):
    add_problem_api = '/api/v4/contests/%s/problems' % config['contest_id']
    
    with open(zip_file, 'rb') as f:
        res = requests.post(config['server'] + add_problem_api,
                            auth=requests.auth.HTTPBasicAuth(
                                    config['username'], config['password']),
                            data={'problem': problem_id},
                            files={'zip': (zip_file, f)})

    if res.status_code != 200 or not res.json()['problem_id']:
        print(ERROR_SYMBOL, 'Error sending the package to the DOMjudge server:',
              res.json())
        return problem_id
    else:
        print(OK_SYMBOL, 'Successfully sent the package to the DOMjudge server.')
        return res.json()['problem_id']

yaml_path = 'all_problems.yaml'


def prepare_argument_parser():
    parser = ArgumentParser(description='Utility script to convert many polygon packages into domjudge packages.')
    parser.add_argument('--polygon', '--from', required=True, help='Directory where the polygon packages can be found.')
    parser.add_argument('--domjudge', '--to', required=True, help='Directory where the DOMjudge packages shall be saved.')
    parser.add_argument('--yaml', required=True, help='Yaml file with a list of the problems to convert (it must contain also some additional metadata for each problem).')
    parser.add_argument('--ignore-version', action='store_true', help='All packages are generated again, ignoring the last converted version. Useful if the p2d script is updated or the letters/colors of the problems are changed.')
    parser.add_argument('--ignore-id', action='store_true', help='The packages are sent to the domjudge server without including their id if they have one. Useful if the problems were deleted in the DOMjudge instance.')
    parser.add_argument('--send', action='store_true', help='Whether the packages updated shall be sent to the domjudge server instance.')
    
    return parser

def p2d_contest(args):
    with open(args.yaml, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)
    problems = config['problems']

    for p in problems:
        old_version = p['version'] if 'version' in p else -1
        if args.ignore_version:
            old_version = -1
        p['version'] = run_p2d_problem(
                p['name'], old_version, p['letter'], p['color'],
                config['contest_name'], args.polygon, args.domjudge)

        if p['version'] == old_version or not args.send: continue
        if args.ignore_id: p['id'] = None
        
        zip_file = os.path.join(args.domjudge, p['letter'] + '.zip')
        new_id = send_package_to_server(zip_file,
                                        p['id'] if 'id' in p else None,
                                        config)
        if new_id:
            p['id'] = new_id
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

def main():
    args = prepare_argument_parser().parse_args()
    p2d_contest(args)

if __name__ == "__main__":
    main()

# TODO:
#       Create whole problem set pdf.