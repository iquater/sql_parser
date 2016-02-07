import re
dir = ''
sql = open(dir, encoding='utf8')

structs = re.split(r'\n{2,}', ''.join([line for line in sql.readlines()]))  # split on separate stucts
new_structs = [re.sub(r'\-\- [\w\s]*\n', '\n', s) for s in structs]  # delete comments

types = {'serial': 'integer',
         'integer': 'integer',
         'float': 'double',
         'text': 'string',
         'timestamp': 'TDateTime',
         'time': 'TTime',
         'boolean': 'boolean'}

classes = {}
for s in new_structs:  # parse structs
    tbl_name = re.search(r'create table \w+', s).group().split(' ')[2]  # getting class name
    # cls_name = 'T' + tbl_name.title()
    # cls = cls_name + ' = class\n  private\n'

    fields = re.findall(r'\n[\w\s]+\s*,*', s)

    cls_var = [];
    getters = [];
    setters = []
    for field in fields:  # getting fields
        field = re.sub(r'\n\s', '', field).strip().replace(',', '').split(" ")  # delete special symbs and split string
        if len(field) < 2:
            continue

        fld_name = field[0]
        if field[1] in types.keys():
            cls_var.append(2 * '  ' + fld_name + '_' + ': {0};'.format(types[field[1]]))  # adding variables to varlist
            getters.append('Get{0}(): {1};'.format(fld_name.title(), types[field[1]]))  # adding getters to getters list
            setters.append('Set{0}({1}: {2});'.format(fld_name.title(), fld_name,
                                                      types[field[1]]))  # adding setters to setters list
    classes[tbl_name] = {'vars': cls_var, 'getters': getters, 'setters': setters}

interfaces = []
for name in classes.keys():  # generate interfaces
    cls_name = 'T' + name.title()
    cls = cls_name + ' = class\n  private\n'

    fields = classes[name]
    cls += '\n'.join(fields['vars'])
    cls += '\n  public'

    cls += '''\n    procedure Load(uid: integer; dbClient: TFDQuery);
    class function LoadAll(dbClient: TFDQuery): TList<integer>; static;
    class function LoadAllWhere(dbClient: TFDQuery; where: string): TList<integer>; static;'''
    cls += '\n    class procedure Save({0}: {1}; dbClient:TFDQuery); static;'.format(name, cls_name)

    for f in fields['getters']:
        cls += '\n    function ' + f
    for p in fields['setters']:
        cls += '\n    procedure ' + p

    cls += '\nend;'
    print(cls)
    interfaces.append(cls);

implementations = []
for name in classes.keys():  # create implementation
    cls_name = 'T' + name.title()
    impl = "{" + "{0}".format(cls_name) + "}\n\n"

    fields = classes[name]
    cls_vars = fields['vars']
    getters = fields['getters']
    setters = fields['setters']
    for i, variable in enumerate(cls_vars):
        getter = getters[i]
        setter = setters[i]

        # create getter implementation:
        impl += 'function ' + '{0}.{1}\n'.format(cls_name, getter)
        var_name = variable.split(':')[0].strip()
        impl += 'begin\n    Result := Self.{0};\nend;\n\n'.format(var_name)
        # create setter implementation:
        impl += 'procedure ' + '{0}.{1}\n'.format(cls_name, setter)
        impl += 'begin\n    Self.{0} := {1};\nend;\n\n'.format(var_name, var_name[0:len(var_name)-1])
    implementations.append(impl)

    # writing vars in class
    """ cls += '\n'.join(cls_var)
    cls += '\n  public'

    # writing common funcs:
    cls += '''\n    procedure Load(uid: integer; dbClient: TFDQuery);
    class function LoadAll(dbClient: TFDQuery): TList<integer>; static;
    class function LoadAllWhere(dbClient: TFDQuery; where: string): TList<integer>; static;'''
    cls += '\n    class procedure Save({0}: {1}; dbClient:TFDQuery); static;'.format(tbl_name, cls_name)

    # writing fields getters and setters
    for f in funcs:
        cls += '\n    function ' + f
    for p in procs:
        cls += '\n    procedure ' + p

    cls += '\nend;'
    print(cls)
    print('****************')"""
