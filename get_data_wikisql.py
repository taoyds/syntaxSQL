import os
import traceback
import re
import sys
import json
import sqlite3
import sqlparse
from os import listdir, makedirs
from collections import OrderedDict
from nltk import word_tokenize, tokenize
from os.path import isfile, isdir, join, split, exists, splitext

from process_sql import get_sql

VALUE_NUM_SYMBOL = 'VALUE'

class Schema:
    """
    Simple schema which maps table&column to a unique identifier
    """
    def __init__(self, schema, table):
        self._schema = schema
        self._table = table
        self._idMap = self._map(self._schema, self._table)

    @property
    def schema(self):
        return self._schema

    @property
    def idMap(self):
        return self._idMap

    def _map(self, schema, table):
        column_names_original = table['column_names_original']
        table_names_original = table['table_names_original']
        #print 'column_names_original: ', column_names_original
        #print 'table_names_original: ', table_names_original
        for i, (tab_id, col) in enumerate(column_names_original):
            if tab_id == -1:
                idMap = {'*': i}
            else:
                key = table_names_original[tab_id].lower()
                val = col.lower()
                idMap[key + "." + val] = i

        for i, tab in enumerate(table_names_original):
            key = tab.lower()
            idMap[key] = i

        return idMap


def strip_query(query):
    '''
    return keywords of sql query
    '''
    query_keywords = []
    query = query.strip().replace(";","").replace("\t","")
    query = query.replace("(", " ( ").replace(")", " ) ")
    query = query.replace(">=", " >= ").replace("=", " = ").replace("<=", " <= ").replace("!=", " != ")


    # then replace all stuff enclosed by "" with a numerical value to get it marked as {VALUE}
    str_1 = re.findall("\"[^\"]*\"", query)
    str_2 = re.findall("\'[^\']*\'", query)
    values = str_1 + str_2
    for val in values:
        query = query.replace(val.strip(), VALUE_NUM_SYMBOL)

    query_tokenized = query.split()
    float_nums = re.findall("[-+]?\d*\.\d+", query)
    query_tokenized = [VALUE_NUM_SYMBOL if qt in float_nums else qt for qt in query_tokenized]
    query = " ".join(query_tokenized)
    int_nums = [i.strip() for i in re.findall("[^tT]\d+", query)]


    query_tokenized = [VALUE_NUM_SYMBOL if qt in int_nums else qt for qt in query_tokenized]
    # print int_nums, query, query_tokenized

    for tok in query_tokenized:
        if "." in tok:
            table = re.findall("[Tt]\d+\.", tok)
            if len(table)>0:
                to = tok.replace(".", " . ").split()
                to = [t.lower() for t in to if len(t)>0]
                query_keywords.extend(to)
            else:
                query_keywords.append(tok.lower())

        elif len(tok) > 0:
            query_keywords.append(tok.lower())

    return query_keywords


def get_schemas_from_json(fpath):
    with open(fpath) as f:
        data = json.load(f)
    db_names = [db['db_id'] for db in data]

    tables = {}
    schemas = {}
    for db in data:
        db_id = db['db_id']
        schema = {} #{'table': [col.lower, ..., ]} * -> __all__
        column_names_original = db['column_names_original']
        table_names_original = db['table_names_original']
        tables[db_id] = {'column_names_original': column_names_original, 'table_names_original': table_names_original}
        for i, tabn in enumerate(table_names_original):
            table = str(tabn.encode("utf8").lower())
            cols = [str(col.encode("utf8").lower()) for td, col in column_names_original if td == i]
            schema[table] = cols
        schemas[db_id] = schema

    return schemas, db_names, tables


def parse_file_and_sql(filepath, schema, db_id):
    f = open(filepath,"r")
    ret = []
    lines = list(f.readlines())
    f.close()
    i = 0
    questions = []
    has_prefix = False
    while i < len(lines):
        line = lines[i].lstrip().rstrip()
        line = line.replace("\r","")
        line = line.replace("\n","")
        if len(line) == 0:
            i += 1
            continue
        if ord('0') <= ord(line[0]) <= ord('9'):
            #remove question number
            if len(questions) != 0:
            	print '\n-----------------------------wrong indexing!-----------------------------------\n'
            	print 'questions: ', questions
            	sys.exit()
            index = line.find(".")
            if index != -1:
                line = line[index+1:]
            if line != '' and len(line) != 0:
                questions.append(line.lstrip().rstrip())
            i += 1
            continue
	if line.startswith("P:"):
	    index = line.find("P:")
	    line = line[index+2:]
	    if line != '' and len(line) != 0:
		questions.append(line.lstrip().rstrip())
	    has_prefix = True
	if (line.startswith("select") or line.startswith("SELECT") or line.startswith("Select") or \
	    line.startswith("with") or line.startswith("With") or line.startswith("WITH")) and has_prefix:
	    sql = [line]
	    i += 1
	    while i < len(lines):
		line = lines[i]
		line = lines[i].lstrip().rstrip()
		line = line.replace("\r","")
		line = line.replace("\n","")
		if len(line) == 0 or len(line.strip()) == 0 or ord('0') <= ord(line[0]) <= ord('9') or \
		   not (line[0].isalpha() or line[0] in ['(',')','=','<','>', '+', '-','!','\'','\"','%']):
		    break
		sql.append(line)
		i += 1
	    sql = " ".join(sql)
	    sql = sqlparse.format(sql, reindent=False, keyword_case='upper')
	    sql = re.sub(r"(<=|>=|=|<|>|,)",r" \1 ",sql)
#			sql = sql.replace("\"","'")
	    sql = re.sub(r"(T\d+\.)\s",r"\1",sql)
	    #if len(questions) != 2:
	    #	print '\n-----------------------------wrong indexing!-----------------------------------\n'
	    #	print 'questions: ', questions
	    #	sys.exit()
	    for ix, q in enumerate(questions):
                try:
                    q = q.encode("utf8")
                    sql = sql.encode("utf8")
                    q_toks = word_tokenize(q)
                    query_toks = word_tokenize(sql)
                    query_toks_no_value = strip_query(sql)
                    sql_label = None

                    sql_label = get_sql(schema, sql)
                    #print("query: {}".format(sql))
                    #print("\ndb_id: {}".format(db_id))
                    #print("query: {}".format(sql))
                    ret.append({'question': q,
                            'question_toks': q_toks,
                            'query': sql,
                            'query_toks': query_toks,
                            'query_toks_no_value': query_toks_no_value,
                            'sql': sql_label,
                            'db_id': db_id})
                except Exception as e:
                    #print("query: {}".format(sql))
                    #print(e)
                    pass
                questions = []
		has_prefix = False
		continue

	i += 1

    return ret


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python get_data.py [dir containing reviewed files] [processed table json file] [output file name e.g. output.json]"
        sys.exit()
    input_dir = sys.argv[1]
    table_file = sys.argv[2]
    output_file = sys.argv[3]

    schemas, db_names, tables = get_schemas_from_json(table_file)
    db_files = [f for f in listdir(input_dir) if f.endswith('.txt')]
    fn_map = {}
    for f in db_files:
        flag = True
        for db in db_names:
            if db.lower() in f.lower():
                flag = False
                fn_map[f] = db
                continue
        if flag == True:
            print "db not found: ", f
    if len(db_files) != len(fn_map.keys()):
        tab_db_files = [f.lower() for f in fn_map.keys()]
        print 'Warning: misspelled files: ', [f for f in db_files if f.lower() not in tab_db_files]
        sys.exit()

    data = []
    for f, db_id in fn_map.items():
        raw_file = join(input_dir, f)
        #print 'reading labeled file for db: ', db_id
	schema = schemas[db_id]
        table = tables[db_id]
        schema = Schema(schema, table)
        data_one = parse_file_and_sql(raw_file, schema, db_id)
        data.extend(data_one)
    with open(output_file, 'wt') as out:
        json.dump(data, out, sort_keys=True, indent=4, separators=(',', ': '))
