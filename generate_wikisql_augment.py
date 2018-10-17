import json
import random
import re
import traceback
import os
import numpy as np
from collections import defaultdict

agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
cond_ops = ['=', '>', '<', 'OP']

random.seed(0)


class Column:
    ATTRIBUTE_TXT = "TXT"
    ATTRIBUTE_NUM = "NUM"
    ATTRIBUTE_GROUP_BY_ABLE = "GROUPBY"

    def __init__(self, name, natural_name, table=None, attributes=None):
        self.name = name
        self.natural_name = natural_name
        self.table = table
        if attributes is not None:
            self.attributes = attributes

    def __str__(self):
        return self.name + "||" + self.natural_name + "||" + str(self.attributes)

found_path_error = 0

class Table(object):
    def __init__(self, name, natural_name):
        self.name = name
        self.natural_name = natural_name
        self.foreign_keys = []

    def add_foreign_key_to(self, my_col, their_col, that_table):
        self.foreign_keys.append((my_col, their_col, that_table))

    def get_foreign_keys(self):
        return self.foreign_keys

    def __str__(self):
        return self.name + "||" + self.natural_name

    def __repr__(self):
        return self.name + "||" + self.natural_name

    def __hash__(self):
        val = 0
        for c in self.name:
            val = val * 10 + ord(c)
        return val

    def __eq__(self, rhs):
        return self.name == rhs.name

    def __ne__(self, rhs):
        return not self.name == rhs.name
        # return self.name + "||" + self.natural_name

# as the column "*" in the data format is marked to be not belonging to any table
# so here's a dummy table for that :(
class DummyTable(Table):
    def add_foreign_key_to(self, my_col, their_col, that_table):
        pass

    def get_foreign_keys(self):
        return []


# models a requirement for a column, will be "attached" to a real column that satisfies the given attribute criteria
class ColumnPlaceholder:
    # e.g. {COLUMN,2,TXT}
    def __init__(self, id_in_pattern, attributes):
        self.id_in_pattern = id_in_pattern
        self.attributes = attributes
        self.column = None

    def attach_to_column(self, column):
        self.column = column


# modelling a SQL pattern along with a bunch of question patterns
class Pattern:
    def __init__(self, schema, json_data):
        self.schema = schema
        self.raw_sql = json_data['SQL Pattern']
        self.raw_questions = json_data['Question Patterns']
        reference_id_to_original_id = json_data['Column Identity']
        self.column_identity = {}

        for reference, original in reference_id_to_original_id.items():
            rid = int(reference)
            oid = int(original)

            self.column_identity[rid] = oid

        raw_column_attributes = json_data['Column Attributes']
        sorted_column_attributes = sorted(
            [(int(column_id), attributes) for column_id, attributes in raw_column_attributes.items()])

        self.column_id_to_column_placeholders = {}
        self.column_placeholders = []

        for column_id, attributes in sorted_column_attributes:
            # see if this references another column
            original_column_id = self.column_identity.get(column_id, None)
            if original_column_id is not None:
                self.column_id_to_column_placeholders[column_id] = self.column_id_to_column_placeholders[
                    original_column_id]
                continue

            # if this does not reference an existing column
            column_placeholder = ColumnPlaceholder(column_id, attributes)
            self.column_placeholders.append(column_placeholder)
            self.column_id_to_column_placeholders[column_id] = column_placeholder

    # given this pattern and a schema, see what new SQL-question pairs can we generate
    def populate(self):
        if self.raw_sql == "SELECT * {FROM, 0}":
            table_name = random.choice(self.schema.orginal_table)
            sql = "SELECT * FROM {}".format(table_name)
            return sql,[
            "list all information about {} .".format(table_name),
            "Show everything on {}".format(table_name),
            "Return all columns in {} .".format(table_name)
        ]
        # find a column for each placeholder
        for column_placeholder in self.column_placeholders:
            all_permissible_columns = self.schema.get_columns_with_attributes(column_placeholder.attributes)
            if len(all_permissible_columns) == 0:
                raise Exception("No possible column found for column {} with required attributes: {}".format(
                    column_placeholder.id_in_pattern,
                    column_placeholder.attributes
                ))
            chosen_column = random.choice(all_permissible_columns)
            column_placeholder.attach_to_column(chosen_column)

        column_id_to_tn = {}

        ## generate processed SQL
        # start with the original (and replace stuff)
        generated_sql = self.raw_sql[:]

        # first identify the FROM replacement tokens
        replacements = []
        for match in re.finditer("{FROM,[,0-9]+}", self.raw_sql):
            raw_from_token = match.group()
            split = raw_from_token[1:-1].split(',')[1:]  # strip the brackets, then the "FROM"
            id_of_columns_involved = [int(x) for x in split]
            # print(id_of_columns_involved)
            # print(self.column_id_to_column_placeholders)
            # print(self.raw_sql)
            placeholders_of_columns_involved = [self.column_id_to_column_placeholders[x] for x in id_of_columns_involved]
            columns_used_for_this_from_clause = [x.column for x in placeholders_of_columns_involved]
            try:
                from_clause, table_to_tn = self.schema.generate_from_clause(columns_used_for_this_from_clause)
            except:
                # traceback.print_exc()
                # print("error generated join")
                # continue
                return "",[]
            # replace this {FROM..} with the generated FROM clause
            replacements.append((raw_from_token, from_clause))

            # add the table_to_tn to our column_id to tn dict
            for column_id in id_of_columns_involved:
                column = self.column_id_to_column_placeholders[column_id].column
                try:
                    tn = table_to_tn[column.table]
                except:
                    global found_path_error
                    found_path_error += 1
                    # print("find path error {}".format(found_path_error))
                    # print "\n-----------------------"
                    # print column
                    # print column.table
                    # print table_to_tn
                    return "",[]
                # print column_id
                column_id_to_tn[column_id] = tn
        # print("column_identity:{}".format(self.column_identity))
        # print("sql template:{}".format(generated_sql))
        # print("column_id_to_tn {}".format(column_id_to_tn))

        for original, new in replacements:
            generated_sql = re.sub(original, new, generated_sql)

        # then replace the column tokens
        replacements = []
        val = None
        table_name = None
        # if self.raw_sql == "SELECT * {FROM, 0}":
        #     print generated_sql
        for match in re.finditer("{[A-Z]+,[,0-9]+}", generated_sql):
            raw_column_token = match.group()
            type, column_id = raw_column_token[1:-1].split(',')
            column_id = int(column_id)

            if type == "COLUMN":
                # find out tn
                if column_id not in column_id_to_tn:
                    column_id = self.column_identity[column_id]
                tn = column_id_to_tn[column_id]
                # find out column name
                column_name = self.column_id_to_column_placeholders[column_id].column.name
                result = "t{}.{}".format(tn, column_name)
            elif type == "VALUE":
                if column_id == 1:
                    result = str(random.randint(1,101))
                    val = result
            elif type == "COLUMN_NAME":
                natural_name = self.column_id_to_column_placeholders[column_id].column.natural_name
                result = natural_name
            elif type == "TABLE_NAME":
                try:
                    natural_name = self.column_id_to_column_placeholders[column_id].column.table.natural_name
                    result = natural_name
                except:
                    result = random.choice(self.schema.orginal_table)
                    table_name = result
            else:
                raise Exception("Unknown type {} in type field".format(type))

            replacements.append((raw_column_token, result))

        for original, new in replacements:
            # print(original,new,generated_sql)
            generated_sql = re.sub(original, new, generated_sql)

        # up to this point, SQL processing is complete
        ## start processing questions
        generated_questions = []
        for question_pattern in self.raw_questions:
            generated_question = question_pattern[:]
            replacements = []
            for match in re.finditer("{[_A-Z]+,[0-9]+}", generated_question):
                raw_column_token = match.group()
                type, column_id = raw_column_token[1:-1].split(',')
                column_id = int(column_id)

                if type == "COLUMN":
                    # find out tn
                    tn = column_id_to_tn[column_id]
                    # find out column name
                    column_name = self.column_id_to_column_placeholders[column_id].column.name
                    result = "t{}.{}".format(tn, column_name)
                elif type == "VALUE":
                        result = val
                elif type == "COLUMN_NAME":
                    natural_name = self.column_id_to_column_placeholders[column_id].column.natural_name
                    result = natural_name
                elif type == "TABLE_NAME":
                    try:
                        natural_name = self.column_id_to_column_placeholders[column_id].column.table.natural_name
                        result = natural_name
                    except:
                        if table_name:
                            result = table_name
                        else:
                            result = random.choice(self.schema.orginal_table)
                else:
                    raise Exception("Unknown type {} in type field".format(type))

                replacements.append((raw_column_token, result))

            for original, new in replacements:
                generated_question = re.sub(original, new, generated_question)

            generated_questions.append(generated_question)

        return generated_sql, generated_questions


class Schema:
    def __init__(self, json_data):
        tables = []
        table_index_to_table_object = {}
        table_name_to_table_object = {}
        next_table_index = 0
        self.orginal_table = json_data['table_names_original']
        # dummy_table = DummyTable("dummy", "dummy")
        # table_index_to_table_object[-1] = dummy_table
        # tables.append(dummy_table)

        for table_name, table_name_natural in zip(json_data['table_names_original'], json_data['table_names']):
            table = Table(table_name, table_name_natural)
            tables.append(table)
            table_index_to_table_object[next_table_index] = table
            table_name_to_table_object[table_name] = table
            next_table_index += 1
        columns = []
        column_and_table_name_to_column_object = {}  # use table name as well to avoid collision
        for (table_index, column_name), column_type, column_names_natural in zip(json_data['column_names_original'],
                                                                                 json_data['column_types'],
                                                                                 json_data['column_names']):
            if table_index == -1:
                continue
            its_table = table_index_to_table_object[table_index]
            if column_type == "text":
                attributes = [Column.ATTRIBUTE_TXT]
            elif column_type == "number":
                attributes = [Column.ATTRIBUTE_NUM]
            else:
                attributes = []
            column = Column(column_name, column_names_natural[1], table=its_table, attributes=attributes)
            column_and_table_name_to_column_object[(column_name, its_table.name)] = column
            columns.append(column)
        # print table_name_to_table_object
        for (from_table_name, from_column_name), (to_table_name, to_column_name) in json_data['foreign_keys']:
            from_table = table_name_to_table_object[from_table_name]
            from_column = column_and_table_name_to_column_object[(from_column_name, from_table_name)]
            to_table = table_name_to_table_object[to_table_name]
            to_column = column_and_table_name_to_column_object[(to_column_name, to_table_name)]

            from_table.add_foreign_key_to(from_column, to_column, to_table)
            to_table.add_foreign_key_to(to_column, from_column, from_table)

        self.all_columns = columns
        self.all_tables = tables

    # e.g. get all the numerical columns that can be group-by'ed over
    def get_columns_with_attributes(self, column_attributes=[]):
        results = []
        for column in self.all_columns:
            # if the column has all the desired attributes
            if all([attribute in column.attributes for attribute in column_attributes]):
                results.append(column)

        return results

    class Join:
        def __init__(self, schema, starting_table):
            self.schema = schema
            self.starting_table = starting_table
            self.table_to_tn = {starting_table: 1}
            self.joins = []

        def find_a_way_to_join(self, table):
            # if this table is already in our join
            if table in self.table_to_tn:
                return

            # BFS
            frontier = []
            visited_tables = set()
            found_path = None
            for table in self.table_to_tn.keys():
                visited_tables.add(table)
                for from_column, to_column, to_table in table.get_foreign_keys():
                    frontier.append((table, from_column, to_column, to_table, []))
            while len(frontier) > 0:
                from_table, from_column, to_column, to_table, path = frontier.pop(0)
                # check if this foreign keys connects to the destination
                path.append((from_table, from_column, to_column, to_table))
                if to_table == table:
                    found_path = path
                    break
                else:
                    for next_from_column, next_to_column, next_to_table in to_table.get_foreign_keys():
                        frontier.append((to_table, next_from_column, next_to_column, next_to_table, path))

            if found_path is None:
                # if a path is not found
                raise Exception(
                    "A path could not be found from the current join {} to table {}".format(self.table_to_tn.keys(),
                                                                                            table))

            for from_table, from_column, to_column, to_table in found_path:
                # allocate a number like "t3" for the next table if necessary
                if to_table not in self.table_to_tn:
                    self.table_to_tn[to_table] = len(self.table_to_tn) + 1
                self.joins.append((from_table, from_column, to_column, to_table))

        def generate_from_clause(self):
            # if no join was needed (only one table)
            if len(self.joins) == 0:
                return "from {} as t1".format(self.starting_table.name)

            from_clause = "from {} as t{} ".format(self.joins[0][0].name, self.table_to_tn[self.joins[0][0]])
            for from_table, from_column, to_column, to_table in self.joins[1:]:
                from_clause += ("join {} as t{}\non t{}.{} = t{}.{}".format(
                    to_table.name,
                    self.table_to_tn[to_table],
                    self.table_to_tn[from_table],
                    from_column.name,
                    self.table_to_tn[to_table],
                    to_column.name
                ))

            return from_clause

    # e.g. I used, doc_name and user_id, how should I write a from clause?
    # not only returning the from clause constructed, but also the mapping from doc_id to t1.doc_id
    def generate_from_clause(self, columns):
        join = self.Join(self, columns[0].table)
        for next_column in columns[1:]:
            join.find_a_way_to_join(next_column.table)

        return join.generate_from_clause(), join.table_to_tn


def load_database_schema(path):
    data = json.load(open(path, "r"))
    schema = Schema(random.choice(data))

    return schema


def load_patterns(path, schema):
    data = json.load(open(path, "r"))
    patterns = []
    for pattern_data in data:
        patterns.append(Pattern(schema, pattern_data))

    return patterns

def generate_every_db(db):
    db_name = db["db_id"]
    col_types = db["column_types"]
    if "number" in col_types:
        try:
            schema = Schema(db)
        except:
            traceback.print_exc()
            print("skip db {}".format(db_name))
            return
        f = open("data_augment/{}.txt".format(db_name),"w")


        idx = 0
        patterns = load_patterns("data_augment/train_patterns.json", schema)

        while idx < 10:
            pattern = random.choice(patterns)
            try:
                sql, questions = pattern.populate()
                #for q in questions:
                if len(questions) != 0:
                    f.write("{}. {}\n".format(1,random.choice(questions).encode("utf8")))
                    f.write("P:\n\n")
                    f.write("{}\n\n".format(sql.encode("utf8")))
                idx += 1
            except:
                pass
        f.close()

    # for pattern in patterns:
    #     try:
    #         sql, questions = pattern.populate()
    #     except:
    #         continue
    #     # for q in questions:
    #     if len(questions) == 0:
    #         continue
    #     f.write("{}. {}\n".format(idx,random.choice(questions)))
    #     f.write("P:\n\n")
    #     f.write("{}\n\n".format(sql))
    #     idx += 1

if __name__ == "__main__":
    dbs = json.load(open("data_augment/wikisql_tables.json"))
    count = 0
    for db in dbs[:]:
        if count % 1000 == 0:
            print("processed {} files...".format(float(count)/len(dbs)))
        generate_every_db(db)
        count += 1
