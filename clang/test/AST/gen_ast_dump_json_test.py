#!/usr/bin/env python

from collections import OrderedDict
from sets import Set
from shutil import copyfile
import argparse
import json
import os
import pprint
import re
import subprocess
    
def normalize(dict_var):
    for k, v in dict_var.items():
        if isinstance(v, OrderedDict):
            normalize(v)
        elif isinstance(v, list):
            for e in v:
                if isinstance(e, OrderedDict):
                    normalize(e)
        elif type(v) is unicode:
            st = v.encode('utf-8')
            if re.match(r"0x[0-9A-Fa-f]+", v):
                dict_var[k] = u'0x{{.*}}'
            elif os.path.isfile(v):
                dict_var[k] = u'{{.*}}'
            else:
                splits = (v.split(u' '))
                out_splits = []
                for split in splits:
                    inner_splits = split.rsplit(u':',2)
                    if os.path.isfile(inner_splits[0]):
                        out_splits.append(
                            u'{{.*}}:%s:%s'
                            %(inner_splits[1],
                              inner_splits[2]))
                        continue
                    out_splits.append(split)

                dict_var[k] = ' '.join(out_splits)

def filter_json(dict_var, filters, out):
    for k, v in dict_var.items():
        if type(v) is unicode:
            st = v.encode('utf-8')
            if st in filters:
                out.append(dict_var)
                break
        elif isinstance(v, OrderedDict):
            filter_json(v, filters, out)
        elif isinstance(v, list):
            for e in v:
                if isinstance(e, OrderedDict):
                    filter_json(e, filters, out)
                
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clang", help="The clang binary (could be a relative or absolute path)",
                        action="store", required=True)
    parser.add_argument("--opts", help="other options",
                        action="store", default='', type=str)
    parser.add_argument("--source", help="the source file. Command used to generate the json will be of the format <clang> -cc1 -ast-dump=json <opts> <source>",
                        action="store", required=True)
    parser.add_argument("--filters", help="comma separated list of AST filters. Ex: --filters=TypedefDecl,BuiltinType",
                        action="store", default='')

    args = parser.parse_args()

    if not args.source:
        print("Specify the source file to give to clang.")
        return -1

    clang_binary = os.path.abspath(args.clang)
    if not os.path.isfile(clang_binary):
        print("clang binary specified not present.")
        return -1

    options = args.opts.split(' ')
    filters = Set(args.filters.split(',')) if args.filters else Set([])
    
    cmd = [clang_binary, "-cc1"]
    cmd.extend(options)

    using_ast_dump_filter = 'ast-dump-filter' in args.opts
        
    cmd.extend(["-ast-dump=json", args.source])

    try:
        json_str = subprocess.check_output(cmd)
    except Exception as ex:
        print("The clang command failed with %s" % ex)
        return -1
    
    out_asts = []
    if using_ast_dump_filter:
        splits = re.split('Dumping .*:\n', json_str)
        if len(splits) > 1:
            for split in splits[1:]:
                j = json.loads(split.decode('utf-8'), object_pairs_hook=OrderedDict)
                normalize(j)
                out_asts.append(j)
    else:
        j = json.loads(json_str.decode('utf-8'), object_pairs_hook=OrderedDict)
        normalize(j)

        if len(filters) == 0:
            out_asts.append(j)
        else:
            #assert using_ast_dump_filter is False,\
            #    "Does not support using compiler's ast-dump-filter "\
            #    "and the tool's filter option at the same time yet."
        
            filter_json(j, filters, out_asts)
        
    partition = args.source.rpartition('.')
    dest_path = '%s-json%s%s' % (partition[0], partition[1], partition[2])

    print("Writing json appended source file to %s." %(dest_path))
    copyfile(args.source, dest_path)    
    with open(dest_path, "a") as f:
        for out_ast in out_asts:
            append_str = json.dumps(out_ast, indent=1, ensure_ascii=False)
            out_str = '\n\n'
            index = 0
            for append_line in append_str.splitlines()[2:]:
                if index == 0:
                    out_str += '// CHECK: %s\n' %(append_line)
                    index += 1
                else:
                    out_str += '// CHECK-NEXT: %s\n' %(append_line)
                    
            f.write(out_str)
    
    return 0
        
if __name__ == '__main__':
    main()
