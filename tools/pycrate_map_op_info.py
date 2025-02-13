#!/usr/bin/python3
# −*− coding: UTF−8 −*−
#/**
# * Software Name : pycrate
# * Version : 0.4.0
# *
# * Copyright © 2018. Benoit Michau. P1sec
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License version 2 as published
# * by the Free Software Foundation. 
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# * GNU General Public License for more details. 
# *
# * You will find a copy of the terms and conditions of the GNU General Public
# * License version 2 in the "license.txt" file or
# * see http://www.gnu.org/licenses/ or write to the Free Software Foundation,
# * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
# *
# *--------------------------------------------------------
# * File Name : tools/pycrate_map_op_info.py
# * Created : 2018-12-13
# * Authors : Benoit Michau 
# *--------------------------------------------------------
#*/

import sys
import argparse
import pprint
pp = pprint.PrettyPrinter(indent=2)

from pycrate_asn1rt.asnobj              import ASN1Obj
ASN1Obj._SILENT = True
#
from pycrate_asn1dir.TCAP_MAPv2v3       import *
from pycrate_mobile.TS29002_MAPAppCtx   import *


# this does not work perfectly, because get_construct_info() is not recursive
# but call get_proto() for SEQUENCE / SET inner components
PRINT_PROTO_EXTCONTAINER = False

SPACE_CONSTRUCT = '    '
SPACE_ERR       = SPACE_CONSTRUCT + '  '

TYPE_CONSTRUCT = {
    TYPE_SEQ,
    TYPE_SEQ_OF,
    TYPE_SET,
    TYPE_SET_OF,
    TYPE_CHOICE
    }


def get_error_info(err, info, wext=True):
    info.append('  errorCode: (local, %.2i)' % err['errorCode'][1])
    if 'ParameterType' in err:
        par = err['ParameterType']
        info.append('    ParameterType: %s (%s)' % (par._typeref.called[1], par.TYPE))
        get_construct_info(par, info, wext=wext, space=SPACE_ERR)
    info.append('')


def get_construct_info(seq, info, wext=True, space=SPACE_CONSTRUCT):
    if PRINT_PROTO_EXTCONTAINER:
        bl = set()
    else:
        bl = set(('extensionContainer', ))
    if seq.TYPE in (TYPE_SEQ, TYPE_SET):
        for c in seq._cont.values():
            info.append(space + '- %s (%s)' % (c._name, c.TYPE))
            if wext and c.TYPE in TYPE_CONSTRUCT and \
            (c._name != 'extensionContainer' or PRINT_PROTO_EXTCONTAINER):
                info.append( 2*space + pp.pformat(c.get_proto(blacklist=bl)[1]).replace('\n', '\n    ' + space) )
        info.append(space + 'mandatory : %s' % ', '.join(seq._root_mand))
    elif seq.TYPE in (TYPE_SEQ_OF, TYPE_SET_OF):
        c = seq._cont
        info.append(space + '- %s (%s)' % (c._typeref.called[1], c.TYPE))
        if wext and c.TYPE in TYPE_CONSTRUCT:
            info.append( 2*space + pp.pformat(c.get_proto(blacklist=bl)[1]).replace('\n', '\n    ' + space) )
    elif seq.TYPE == TYPE_CHOICE:
        for c in seq._cont.values():
            info.append(space + '- %s (%s)' % (c._name, c.TYPE))
            if wext and c.TYPE in TYPE_CONSTRUCT:
                info.append( 2*space + pp.pformat(c.get_proto(blacklist=bl)[1]).replace('\n', '\n    ' + space) )


def show_infos(val, werr, wext):
    
    print()
    vers = ''
    info = ['OPERATION content: %s\n' % ' - '.join(sorted(val.keys()))]
    
    if 'ArgumentType' in val:
        arg  = val['ArgumentType']
        vers = arg._typeref.called[0].split('-')[0]
        info.append('  ArgumentType: %s (%s)' % (arg._typeref.called[1], arg.TYPE))
        get_construct_info(arg, info, wext)
        info.append('')
    
    if 'ResultType' in val:
        res = val['ResultType']
        if res._typeref.called[0].split('-')[0] != vers:
            print('[ERR] version error')
        info.append('  ResultType: %s (%s)' % (res._typeref.called[1], res.TYPE))
        get_construct_info(res, info, wext)
        info.append('')
    
    if werr and 'Errors' in val:
        err = val['Errors']
        for e in err.getv():
            get_error_info(e, info, wext)
    
    if vers == 'MAPv2':
        info.insert(0, 'MAP version 1 and 2')
    elif vers:
        info.insert(0, 'MAP version 3 and over')
    else:
        info.insert(0, 'MAP version unknown')
    
    print('\n'.join(info))


def show_appctx(oc):
    
    aci = get_application_ctxs(oc, 'I')
    if aci:
        print()
        print('Initiator in MAP application context:')
        for acname, ac in aci.items():
            print('  - %-40s (%s)' % (acname, ' '.join(map(str, ac['code']))))
            print('    {%s} -> {%s}' % (', '.join(ac['InitiatorIn'].getv()), ', '.join(ac['ResponderIn'].getv())))
    
    acr = get_application_ctxs(oc, 'R')
    if acr:
        print()
        print('Responder in MAP application context:')
        for acname, ac in acr.items():
            print('  - %-40s (%s)' % (acname, ' '.join(map(str, ac['code']))))
            ocini = []
            if 'InitiatorConsumerOf' in ac:
                for opval in ac['InitiatorConsumerOf'].getv():
                    if 'Supplier' in opval:
                        for oval in opval['Supplier'].getv():
                            ocini.append(oval['operationCode'][1])
            print('    MAP opcode initiating: %s' % ', '.join(map(str, ocini)))
            print('    {%s} -> {%s}' % (', '.join(ac['InitiatorIn'].getv()), ', '.join(ac['ResponderIn'].getv())))


def print_operation_infos(args):
    Op = GLOBAL.MOD['MAPv2v3-Protocol']['Supported-MAP-Operations']
    if args.o == []:
        oc = list(range(0x100))
    else:
        oc = args.o[:]
    for i in oc:
        vals = Op.get('operationCode', ('local', i))
        if vals[0] == 'U':
            print()
            print('-'*80)
            print('-'*25, ' operationCode: (local, %.2i) ' % i, '-'*25)
            print('-'*80)
            val = vals[1]
            show_infos(val, args.e, args.x)
        elif vals[0] == 'M':
            print()
            print('-'*80)
            print('-'*25, ' operationCode: (local, %.2i) ' % i, '-'*25)
            print('-'*80)
            for val in vals[1]:
                show_infos(val, args.e, args.x)
        show_appctx(i)


def main():
    parser = argparse.ArgumentParser(description='print information related to MAP '\
        'procedures providing their operation code integral value')
    parser.add_argument('-o', type=int, nargs='+', help='MAP operation code', default=[])
    parser.add_argument('-e', action='store_true', help='add procedure-related errors')
    parser.add_argument('-x', action='store_true', help='add extended data structures')
    args = parser.parse_args()
    #
    print_operation_infos(args)
    return 0


if __name__ == '__main__':
    sys.exit(main())

