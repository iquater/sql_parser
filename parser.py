import re
dir = ''
sql = open(dir, encoding='utf8')

structs = re.split(r'\n{2,}', ''.join([line for line in sql.readlines()]))  # split on separate stucts
new_structs = [re.sub(r'\-\- [\w\s]*\n', '\n', s) for s in structs]  # delete comments

sql.close()

types = {'serial': 'integer',
         'integer': 'integer',
         'float': 'double',
         'text': 'string',
         'timestamp': 'TDateTime',
         'time': 'TTime',
         'boolean': 'boolean'}

classes = {}
references = {} # links between tables {main: referencing}
for s in new_structs:  # parse structs
    tbl_name = re.search(r'create table \w+', s).group().split(' ')[2]  # getting class name
    # cls_name = 'T' + tbl_name.title()
    # cls = cls_name + ' = class\n  private\n'

    fields = re.findall(r'\n[\w\s]+\s*,*', s)

    fk = re.findall(r'foreign [()\w\s]*', s, re.IGNORECASE)

    # hack: when table includes more than one references,
    # consider, that first referencing on primary key.
    #if len(fk) > 1: fk.pop(1)

    for k in fk:
        main_table = re.findall(r'references ([\w]+)\([\w]+\)', k, re.IGNORECASE) #get main(referenced) table name
        references[main_table[0]] = tbl_name
        print(main_table, tbl_name)

    cls_var = []
    getters = []
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

#exit()
#assert (False)
interfaces = []
for name in classes.keys():  # generate interfaces
    cls_name = 'T' + name.title()
    cls = cls_name + ' = class\n  private\n'

    fields = classes[name]
    cls += '\n'.join(fields['vars'])

    if name in references.keys():
        ref_name = references[name]
        if ref_name == 'plane' or ref_name == 'satellite':
            cls += '\n    {0}: TList<{1}>;'.format(ref_name, 'T'+ref_name.title())
        else:
            cls += '\n    {0}: {1};'.format(ref_name, 'T'+ref_name.title())

    cls += '\n  public'

    if name in references.keys():
        ref_name = references[name]
        if ref_name == 'plane' or ref_name == 'satellite':
            cls += '\n    constructor Create;'
            cls += '\n    destructor Destroy;'
            cls += '\n    procedure Clear{0}List();'.format(ref_name.title())
            cls += '\n    procedure Load{0}List(dbClient: TFDQuery);'.format(ref_name.title())

    cls += ('\n    procedure Load(uid: integer; dbClient: TFDQuery);\n'
            '    class function LoadAll(dbClient: TFDQuery): TList<integer>; static;\n'
            '    class function LoadAllWhere(dbClient: TFDQuery; where: string): TList<integer>; static;')
    cls += '\n    class procedure Save({0}: {1}; dbClient:TFDQuery); static;'.format(name, cls_name)

    for f in fields['getters']:
        cls += '\n    function ' + f
    for p in fields['setters']:
        cls += '\n    procedure ' + p

    cls += '\nend;'
    print(cls)
    interfaces.append(cls)

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

    class_vars = [v.split(':')[0].strip() for v in cls_vars]
    query_vars = [v[0:len(v)-1] for v in class_vars]
    lines = []
    for v in cls_vars:
        v_name = v.split(':')[0].strip()
        v_type = v.split(':')[1].strip().replace(';', '')
        if v_type.lower() == "tdatetime" or v_type.lower() == "ttime":
            v_type = "DateTime"
        elif v_type.lower() == "double":
            v_type = "Float"

        lines.append("  Self.{0} := dbClient.FieldByName('{1}').As{2};\n".
                     format(v_name, v_name[0:len(v_name)-1], v_type.title()))

    # function-loader: need initialize TList (if class has it)
    # add Constructor, destructor and list clearer

    if name in references.keys():
        ref_name = references[name]
        if ref_name == 'satellite' or ref_name == 'plane':
            impl += ("constructor {0}.Create;\n"
                     "begin\n"
                     "  {1} := TList<{2}>.Create;\n"
                     "end;\n\n").format(cls_name, ref_name, 'T' + ref_name.title())
            impl += ("destructor {0}.Destroy;\n"
                     "var \n"
                     " i: integer;\n"
                     "begin\n"
                     "  for i:=0 to {1}.Count - 1 do\n"
                     "  begin\n"
                     "    TObject({1}[i]).Free;\n"
                     "  end;\n"
                     "  {1}.Free;\n"
                     "end;\n\n").format(cls_name, ref_name)

            impl += ("procedure {0}.Clear{1}List();\n"
                     "var\n"
                     "  i : integer;\n"
                     "begin\n"
                     "  for i :=0 to {2}.Count - 1 do\n"
                     "  begin"
                     "    TObject({2}[i]).Free;\n"
                     "  end;"
                     "  {2}.Clear;\n"
                     "end;\n\n").format(cls_name, ref_name.title(), ref_name)

            impl += ("procedure {0}.Load{1}List(dbClient: TFDQuery);\n"
                     "var\n"
                     "  uids: TList<Integer>;\n"
                     "  query: string;\n"
                     "  i: integer;\n"
                     "  {2} : T{1};\n"
                     "begin\n"
                     "  Clear{1}List();\n"
                     "  query := Format('uid_{3} is %d', [uid_]);\n"
                     "  uids := T{1}.LoadAllWhere(dbClient, query);\n"
                     "  for i := 0 to uids.Count -1 do\n"
                     "  begin\n"
                     "    {2} := T{1}.Create();\n"
                     "    {2}.Load(uids[i], dbClient);\n"
                     "    {4}.add({2});\n"
                     "  end;\n"
                     "  for i := 0 to uids.Count - 1 do\n"
                     "  begin\n"
                     "    TObject(uids[i]).Free;\n"
                     "  end;\n"
                     "  uids.Clear;\n"
                     "end;\n\n").format(cls_name, ref_name.title(),
                                        ref_name+ '_unit', name, ref_name )

            #sub_impl += ("  if {0}.Count > 0 then"
            #             "  begin"
            #             "    Clear{0}List();"
            #             "  end"
            #             "  ")


    query = 'select * from {0} where uid = :id'.format(name)
    impl += 'procedure' + ' {0}.Load(uid: integer; dbClient: TFDQuery);'.format(cls_name)
    impl += '\nvar\n  query:string;\n'
    impl += ("begin\n"
             "  dbClient.SQL.Text:='{0}';\n"
             "  dbClient.ParamByName('id').AsInteger := uid;\n"
             "  dbClient.Open();\n"
             "  while not dbClient.Eof do\n"
             "  begin\n"
             "    {1}\n"
             "    dbClient.Next;\n"
             "  end;\n"
             "end;\n\n").format(query, '  '.join(lines))

    impl += 'class function' + ' {0}.LoadAll(dbClient: TFDQuery): TList<integer>;'.format(cls_name)
    query = 'select uid from {0}'.format(name)
    impl += '\nvar\n  res: TList<integer>; query:string;\n'
    impl += ("begin\n"
             "  res := TList<integer>.Create;\n"
             "  dbClient.SQL.Text := '{0}';\n"
             "  dbClient.Open();\n"
             "  while not dbClient.Eof do\n"
             "  begin\n"
             "    res.Add(dbClient.FieldByName('uid').AsInteger);\n"
             "    dbClient.Next;\n"
             "  end;\n"
             "  Result:= res;\n"
             "end;\n\n").format(query)

    impl += 'class function' + ' {0}.LoadAllWhere(dbClient: TFDQuery; where: string): TList<integer>;'.format(cls_name)
    impl += '\nvar\n  res: TList<integer>;\n'
    impl += ("begin\n"
             "  res := TList<integer>.Create;\n"
             "  dbClient.SQL.Text := '{0} ' + where;\n"
             "  dbClient.Open();\n"
             "  while not dbClient.Eof do\n"
             "  begin\n"
             "    res.Add(dbClient.FieldByName('uid').AsInteger);\n"
             "    dbClient.Next;\n"
             "  end;\n"
             "  Result:= res;\n"
             "end;\n\n").format(query)

    impl += 'class procedure' + ' {0}.Save({1}: {0}; dbClient: TFDQuery);\n'.format(cls_name, name)
    impl += 'begin\nend;\n'

    implementations.append(impl)


res_file = open('F:\\projects\\sql\\res.pas', 'w', encoding='utf8')
res_file.write('unit res;\n\ninterface')

res_file.write("""\n\nuses System.Generics.Collections, FireDAC.Stan.Intf, FireDAC.Stan.Option,
  FireDAC.Stan.Error, FireDAC.UI.Intf, FireDAC.Phys.Intf, FireDAC.Stan.Def,
  FireDAC.Stan.Pool, FireDAC.Stan.Async, FireDAC.Phys, FireDAC.Stan.Param,
  FireDAC.DatS, FireDAC.DApt.Intf, FireDAC.DApt, Data.DB, FireDAC.Comp.DataSet,
  FireDAC.Comp.Client, Vcl.StdCtrls, System.SysUtils ;""")

res_file.write("\n\ntype\n\n")
for cls in classes.keys():
    res_file.write("{0} = class;\n".format('T' + cls.title()))

for cls in interfaces:
    res_file.write(cls + '\n')

res_file.write('\nimplementation\n')

for impl in implementations:
    res_file.write(impl + '\n')

res_file.write('end.')

res_file.close()