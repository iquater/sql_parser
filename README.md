# sql_parser
Код для разбора sql-скрипта для создания таблиц вида:
create table example(
 uid serial unique,
 name text);

и превращения их в Delphi- классы

TExample = class
  private
    uid_: integer;
    name_: string;
  public
    function GetUid(): integer;
    procedure SetUid(uid: integer);
end;
