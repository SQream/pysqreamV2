import time
from datetime import datetime, date, timezone
from numpy.random import randint, uniform
from queue import Queue
from time import sleep
import threading, sys, os
import pytest
from tests.logger import Logger
import pysqream_blue


q = Queue()
varchar_length = 10
nvarchar_length = 10
max_bigint = sys.maxsize if sys.platform not in ('win32', 'cygwin') else 2147483647

col_types = {'bool', 'tinyint', 'smallint', 'int', 'bigint', 'real', 'double', 'date', 'datetime', 'text'}


pos_test_vals = {'bool': [0, 1, True, False, 2],
                 'tinyint': [randint(0, 255), randint(0, 255), 0, 255],
                 'smallint': [randint(-32768, 32767), 0, -32768, 32767],
                 'int': [randint(-2147483648, 2147483647), 0, -2147483648, 2147483647],
                 'bigint': [randint(1-max_bigint, max_bigint), 0, 1-max_bigint, max_bigint],
                 'real': [round(uniform(1e-6, 1e6), 5), 837326.52428],   # float('nan')
                 'double': [uniform(1e-6, 1e6)],  # float('nan')
                 'date': [date(1998, 9, 24), date(2020, 12, 1), date(1997, 5, 9), date(1993, 7, 13)],
                 'datetime': [datetime(1001, 1, 1, 10, 10, 10), datetime(1997, 11, 30, 10, 10, 10), datetime(1987, 7, 27, 20, 15, 45), datetime(1993, 12, 20, 17, 25, 46)],
                 'text': ['א', 'א  ', '', 'ab א']}

# After parameterized query supported -
neg_test_vals = {'tinyint': (258, 3.6, 'test',  (1997, 5, 9), (1997, 12, 12, 10, 10, 10)),
                 'smallint': (40000, 3.6, 'test', (1997, 5, 9), (1997, 12, 12, 10, 10, 10)),
                 'int': (9999999999, 3.6, 'test',  (1997, 5, 9), (1997, 12, 12, 10, 10, 10)),
                 'bigint': (92233720368547758070, 3.6, 'test', (1997, 12, 12, 10, 10, 10)),
                 'real': ('test', (1997, 12, 12, 10, 10, 10)),
                 'double': ('test', (1997, 12, 12, 10, 10, 10)),
                 'date': (5, 3.6, (-8, 9, 1), (2012, 15, 6), (2012, 9, 45), 'test', False, True),
                 'datetime': (5, 3.6, (-8, 9, 1, 0, 0, 0), (2012, 15, 6, 0, 0, 0), (2012, 9, 45, 0, 0, 0), (2012, 9, 14, 26, 0, 0), (2012, 9, 14, 13, 89, 0), 'test', False, True),
                 'text': (5, 3.6, (1, 2), (1997, 12, 12, 10, 10, 10), False, True)}


def connect_pysqream_blue(domain, access_token, use_ssl=True, use_logs=False, log_path=None, log_level='INFO'):
    if use_logs:
        pysqream_blue.set_log_path(log_path)
    return pysqream_blue.connect(host=domain, use_ssl=use_ssl,
                                 access_token=access_token, use_logs=use_logs, log_level=log_level)


class Query():

    def __init__(self, con):
        self.con = con

    def fetch(self, query):
        cur = self.con.cursor()
        cur.execute(query)
        res = cur.fetchall()
        cur.close()
        return res

    def execute(self, query):
        cur = self.con.cursor()
        cur.execute(query)
        cur.close()

    def fetchmany(self, query, number):
        cur = self.con.cursor()
        cur.execute(query)
        res = cur.fetchmany(number)
        cur.close()
        return res

    def fetchone(self, query):
        cur = self.con.cursor()
        cur.execute(query)
        res = cur.fetchone()
        cur.close()
        return res


class TestBase():

    @pytest.fixture()
    def domain(self, pytestconfig):
        return pytestconfig.getoption("domain")

    @pytest.fixture()
    def access_token(self, pytestconfig):
        return pytestconfig.getoption("access_token")

    @pytest.fixture()
    def log_path(self, pytestconfig):
        return pytestconfig.getoption("log_path", default=None)

    @pytest.fixture()
    def use_logs(self, pytestconfig):
        return pytestconfig.getoption("use_logs", default=False)

    @pytest.fixture()
    def log_level(self, pytestconfig):
        return pytestconfig.getoption("log_level", default='INFO')

    @pytest.fixture(autouse=True)
    def Test_setup_teardown(self, domain, access_token, use_logs, log_path, log_level):
        self.domain = domain
        self.access_token = access_token
        Logger().info("Before Scenario")
        Logger().info(f"Connect to server with domain {domain}")
        self.con = connect_pysqream_blue(domain, access_token, use_logs=use_logs, log_path=log_path, log_level=log_level)
        self.query = Query(self.con)
        yield
        Logger().info("After Scenario")
        self.con.close()
        Logger().info(f"Close Session to server {domain}")

    def fetch(self, query):
        return self.query.fetch(query)

    def execute(self, query):
        self.query.execute(query)

    def fetchmany(self, query, number):
        return self.query.fetchmany(query, number)

    def fetchone(self, query):
        return self.query.fetchone(query)

class TestBaseWithoutBeforeAfter():
    @pytest.fixture()
    def domain(self, pytestconfig):
        return pytestconfig.getoption("domain")

    @pytest.fixture()
    def access_token(self, pytestconfig):
        return pytestconfig.getoption("access_token")

    @pytest.fixture(autouse=True)
    def Test_setup_teardown(self, domain, access_token):
        self.domain = domain
        self.access_token = access_token
        yield


class TestDebug(TestBase):

    def test_debug(self):
        # con = connect_pysqream_blue(self.domain, use_ssl=False)
        # cur = con.cursor()
        # cur.execute("select 1")
        # res1 = cur.fetchall()
        # cur.close()
        # con.close()
        #
        # con2 = connect_pysqream_blue(self.domain, use_ssl=False)
        # cur = con2.cursor()
        # cur.execute("select 2")
        # res2 = cur.fetchall()
        # cur.close()
        # con2.close()

        res1 = self.query.fetch("select 1")
        res2 = self.query.fetch("select 2")
        print(res1)
        print(res2)


class TestConnection(TestBaseWithoutBeforeAfter):

    def test_connection(self):

        Logger().info("connect and run select 1")
        con = connect_pysqream_blue(self.domain, self.access_token, use_ssl=False)
        cur = con.cursor()
        try:
            cur.execute("select 1")
        except Exception as e:
            if "SQreamd connection interrupted" not in repr(e):
                raise Exception("bad error message")
        cur.close()
        Logger().info("Connection tests - wrong ip")
        try:
            pysqream_blue.connect(host='123.4.5.6', port='443', database='master', username='sqream',
                                  password='sqream',use_ssl=False, access_token=self.access_token)
        except Exception as e:
            if "Error from grpc while attempting to open database connection" not in repr(e):
                raise Exception("bad error message")

        Logger().info("Connection tests - wrong port")
        try:
            pysqream_blue.connect(host=self.domain, port='6000', database='master', username='sqream',
                                  password='sqream', use_ssl=False, access_token=self.access_token)
        except Exception as e:
            if "Error from grpc while attempting to open database connection" not in repr(e):
                raise Exception("bad error message")

        Logger().info("Connection tests - wrong database")
        try:
            pysqream_blue.connect(host=self.domain, port='443', database='wrong_db', username='sqream',
                                  password='sqream', use_ssl=False, access_token=self.access_token)
        except Exception as e:
            if "database \"wrong_db\" does not exist" not in repr(e).replace("""\\""", ''):
                raise Exception("bad error message")

        Logger().info("Connection tests - wrong username")
        try:
            pysqream_blue.connect(host=self.domain, port='443', database='master', username='wrong_username',
                                  password='sqream', use_ssl=False, access_token=self.access_token)
        except Exception as e:
            if "role \'wrong_username\' doesn't exist" not in repr(e).replace("""\\""", ''):
                raise Exception("bad error message")

        Logger().info("Connection tests - wrong password")
        try:
            pysqream_blue.connect(host=self.domain, port='443', database='master', username='sqream',
                                  password='wrong_pw', use_ssl=False, access_token=self.access_token)
        except Exception as e:
            if "wrong password for role 'sqream'" not in repr(e).replace("""\\""", ''):
                raise Exception("bad error message")

        Logger().info("Connection tests - close() function")
        con = connect_pysqream_blue(self.domain, self.access_token)
        cur = con.cursor()
        cur.close()
        try:
            cur.execute('select 1')
        except Exception as e:
            if "Statement has been closed" not in repr(e):
                raise Exception("bad error message")

        Logger().info("Connection tests - Trying to close a connection that is already closed with close()")
        con = connect_pysqream_blue(self.domain, self.access_token)
        con.close()
        try:
            con.close()
        except Exception as e:
            if "Trying to close a connection that's already closed" not in repr(e):
                raise Exception("bad error message")


class TestPositive(TestBase):

    def test_positive(self):

        for col_type in col_types:
            trimmed_col_type = col_type.split('(')[0]

            Logger().info(f'Positive tests - Inserted values test for column type {col_type}')
            Logger().info(f"create or replace table test (t_{trimmed_col_type} {col_type})")
            self.execute(f"create or replace table test (t_{trimmed_col_type} {col_type})")
            for val in pos_test_vals[trimmed_col_type]:
                # cur.execute('truncate table test')
                self.execute('truncate table test')
                if type(val) in [date, datetime, str]:
                    Logger().info(f"insert into test values (\'{val}\')")
                    self.execute(f"insert into test values (\'{val}\')")
                # elif type(val) == bool:
                #     Logger().info(f"insert into test values ({str(val).lower()})")
                #     self.execute(f"insert into test values ({str(val).lower()})")
                else:
                    Logger().info(f"insert into test values ({val})")
                    self.execute(f"insert into test values ({val})")
                Logger().info("select * from test")
                res = self.fetch("select * from test")[0][0]
                # Compare
                if val != res:
                    if trimmed_col_type not in ('bool', 'varchar', 'date', 'datetime', 'real'):
                        Logger().info((repr(val), type(val), repr(res), type(res)))
                        raise Exception("TEST ERROR: No match between the expected result to the returned result. expected to get {}, instead got {} on datatype {}".format(repr(val), repr(res), trimmed_col_type))
                    elif trimmed_col_type == 'bool' and val != 0:
                        if res is not True:
                            raise Exception("TEST ERROR: No match between the expected result to the returned result. expected to get 'True', instead got {} on datatype {}".format(repr(res), trimmed_col_type))
                    elif trimmed_col_type == 'varchar' and val.strip() != res:
                        raise Exception("TEST ERROR: No match between the expected result to the returned result. expected to get {}, instead got {} on datatype {}".format(repr(val), repr(res), trimmed_col_type))
                    elif trimmed_col_type in ('date', 'datetime') and datetime(*val) != res and date(*val) != res:
                        raise Exception("TEST ERROR: No match between the expected result to the returned result. expected to get {}, instead got {} on datatype {}".format(repr(val), repr(res), trimmed_col_type))
                    elif trimmed_col_type == 'real' and abs(res-val) > 0.1:
                        # Single precision packing and unpacking is inaccurate:
                        # unpack('f', pack('f', 255759.83335))[0] == 255759.828125
                        raise Exception("TEST ERROR: No match between the expected result to the returned result. expected to get {}, instead got {} on datatype {}".format(repr(val), repr(res), trimmed_col_type))

            # Network insert not supported
            # Logger().info(f'Positive tests - Null test for column type: {col_type}')
            # self.con.execute("create or replace table test (t_{} {})".format(trimmed_col_type, col_type))
            # self.con.executemany('insert into test values (?)', [(None,)])
            # status = self.con.execute('select * from test')
            # res = self.con.fetchall()[0][0]
            # if res not in (None,):
            #     raise Exception("TEST ERROR: Error setting null on column type: {}\nGot: {}, {}".format(trimmed_col_type, res, type(res)))

        # Network insert not supported
        # Logger().info("Positive tests - Case statement with nulls")
        # self.con.execute("create or replace table test (xint int)")
        # self.con.executemany('insert into test values (?)', [(5,), (None,), (6,), (7,), (None,), (8,), (None,)])
        # self.con.executemany("select case when xint is null then 1 else 0 end from test")
        # expected_list = [0, 1, 0, 0, 1, 0, 1]
        # res_list = []
        # res_list += [x[0] for x in self.con.fetchall()]
        # if expected_list != res_list:
        #     raise Exception("expected to get {}, instead got {}".format(expected_list, res_list))
        Logger().info("Positive tests - Testing select true/false")
        res = self.fetch("select false")[0][0]
        if res != 0:
            raise Exception("Expected to get result 0, instead got {}".format(res))
        res = self.fetch("select true")[0][0]
        if res != 1:
            raise Exception("Expected to get result 1, instead got {}".format(res))

        Logger().info("Positive tests - Running a statement when there is an open statement")
        self.execute("select 1")
        sleep(10)
        res = self.fetch("select 1")[0][0]
        if res != 1:
            raise Exception(f'expected to get result 1, instead got {res}')


class TestNegative(TestBase):

    def test_negative(self):
        ''' Negative Set/Get tests '''

        # not supported network insert
        # for col_type in col_types:
        #     if col_type == 'bool':
        #         continue
        #     Logger().info("Negative tests for column type: {}".format(col_type))
        #     trimmed_col_type = col_type.split('(')[0]
        #     Logger().info("prepare a table")
        #     self.con.execute("create or replace table test (t_{} {})".format(trimmed_col_type, col_type))
        #     for val in neg_test_vals[trimmed_col_type]:
        #         Logger().info("Insert value {} into data type {}".format(repr(val), repr(trimmed_col_type)))
        #         rows = [(val,)]
        #         try:
        #             self.con.executemany("insert into test values (?)", rows)
        #         except Exception as e:
        #             if "Error packing columns. Check that all types match the respective column types" not in repr(e):
        #                 raise Exception(f'bad error message')

        # Logger().info("Negative tests - Inconsistent sizes test")
        # self.con.execute("create or replace table test (xint int, yint int)")
        # try:
        #     self.con.executemany('insert into test values (?, ?)', [(5,), (6, 9), (7, 8)])
        # except Exception as e:
        #     if "Incosistent data sequences passed for inserting. Please use rows/columns of consistent length" not in repr(e):
        #         raise Exception(f'bad error message')

        Logger().info("Negative tests - Nvarchar - Conversion of a varchar to a smaller length")
        self.execute("create or replace table test (test nvarchar(10))")
        try:
            self.execute("insert into test values ('aa12345678910')")
        except Exception as e:
            if "value \'aa12345678910\' is too long for column \'test\' of type TEXT(10)" not in repr(e).replace("""\\""", ''):
                raise Exception(f'bad error message')

        Logger().info("Negative tests - Incorrect usage of fetchmany - fetch without a statement")
        self.execute("create or replace table test (xint int)")
        cur = self.con.cursor()
        try:
            cur.fetchmany(2)
        except Exception as e:
            if "No open statement while attempting fetch operation" not in repr(e):
                raise Exception(f'bad error message')
        cur.close()

        Logger().info("Negative tests - Incorrect usage of fetchall")
        self.execute("create or replace table test (xint int)")
        cur = self.con.cursor()
        cur.execute("select * from test")
        try:
            cur.fetchall(5)
        except Exception as e:
            if "Bad argument to fetchall" not in repr(e):
                raise Exception(f'bad error message')
        cur.close()

        Logger().info("Negative tests - Incorrect usage of fetchone")
        self.execute("create or replace table test (xint int)")
        cur = self.con.cursor()
        cur.execute("select * from test")
        try:
            cur.fetchone(5)
        except Exception as e:
            if "Bad argument to fetchone" not in repr(e):
                raise Exception(f'bad error message')
        cur.close()

        # not supported network insert
        # Logger().info("Negative tests - Parametered query tests")
        # params = 6
        # self.con.execute("create or replace table test (xint int)")
        # self.con.executemany('insert into test values (?)', [(5,), (6,), (7,)])
        # try:
        #     self.con.execute('select * from test where xint > ?', str(params))
        # except Exception as e:
        #     if "Parametered queries not supported" not in repr(e):
        #         raise Exception(f'bad error message')
        Logger().info("Negative tests - running execute on a closed cursor")
        cur = self.con.cursor()
        cur.close()
        try:
            cur.execute("select 1")
        except Exception as e:
            if "Statement has been closed" not in repr(e):
                raise Exception(f'bad error message')


# Network insert not supported
# def parametered_test():
#     ''' Parametered query tests '''
#
#     global TESTS_PASS
#
#     print ('\nParametered Tests')
#     print ('-----------------')
#
#     params = 6,
#     con.execute(f'create or replace table test (t_int int)')
#     con.executemany('insert into test values (?)', [(5,), (6,), (7,)])
#     con.execute('select * from test where t_int > ?', params)
#     res = con.fetchall()
#
#     if res[0][0] != 7:
#         print (f"parametered test fail, expected value {params} but got {res[0][0]}")
#         TESTS_PASS = False


class TestFetch(TestBase):

    def test_fetch(self):

        Logger().info("Fetch tests - positive fetch tests")
        self.execute("create or replace table test (xint int)")
        # network insert not supported
        # self.con.executemany('insert into test values (?)', [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,)])
        for i in range(1, 10):
            self.execute(f'insert into test values ({i})')

        # fetchmany(1) vs fetchone()
        res = self.fetchmany("select * from test", 1)[0][0]
        res2 = self.fetchone("select * from test")[0][0]
        if res != res2:
            raise Exception(f"fetchmany(1) and fetchone() didn't return the same value. fetchmany(1) is {res} and fetchone() is {res2}")
        # fetchmany(-1) vs fetchall()
        res3 = self.fetchmany("select * from test", -1)[0][0]
        res4 = self.fetch("select * from test")[0][0]
        if res3 != res4:
            raise Exception("fetchmany(-1) and fetchall() didn't return the same value. fetchmany(-1) is {} and fetchall() is {}".format(res3, res4))
        # fetchone() loop
        cur = self.con.cursor()
        cur.execute("select * from test")
        for i in range(1, 10):
            x = cur.fetchone()[0][0]
            if x != i:
                raise Exception("fetchone() returned {} instead of {}".format(x, i))
        cur.close()

        Logger().info("Fetch tests - combined fetch functions")
        self.execute("create or replace table test (xint int)")
        # network insert not supported
        # self.con.executemany('insert into test values (?)', [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,)])
        for i in range(1, 10):
            self.execute(f'insert into test values ({i})')
        cur = self.con.cursor()
        cur.execute("select * from test")
        expected_list = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        res_list = []
        res_list.append(cur.fetchone()[0][0])
        res_list += [x[0] for x in cur.fetchmany(2)]
        res_list.append(cur.fetchone()[0][0])
        res_list += [x[0] for x in cur.fetchall()]
        if expected_list != res_list:
            raise Exception("expected to get {}, instead got {}".format(expected_list, res_list))
        cur.close()

        Logger().info("Fetch tests - fetch functions after all the data has already been read")
        self.execute("create or replace table test (xint int)")
        # network insert not supported
        # self.con.executemany('insert into test values (?)', [(1,)])
        self.execute('insert into test values (1)')
        cur = self.con.cursor()
        cur.execute("select * from test")
        x = cur.fetchone()[0]
        res = cur.fetchone()
        if res is not None:
            raise Exception(f"expected to get an empty result from fetchone, instead got {res}")
        try:
            cur.fetchall()
        except Exception as e:
            if "No open statement while attempting fetch operation" not in repr(e):
                raise Exception(f'bad error message')

        try:
            cur.fetchmany(1)
        except Exception as e:
            if "No open statement while attempting fetch operation" not in repr(e):
                raise Exception(f'bad error message')

        cur.close()


class TestCursor(TestBase):
    def test_array(self):
        Logger().info("Cursor tests - test array")
        #init state
        self.con.cursor().execute("create or replace table a(x int[])").close()
        self.con.cursor().execute("insert into a values (Array[1]),( Array[1,2,3])").close()

        #first test
        cur = self.con.cursor().execute("select * from a")
        res1 = cur.fetchall()
        expected_result = [([1],), ([1, 2, 3],)]
        if res1 != expected_result:
            raise Exception("expected to get {}, instead got {}".format(expected_result, res1))
        Logger().info(res1)
        cur.close()

        #second test
        cur = self.con.cursor()
        cur.execute("select Array['hgjh','jj']")
        res1 = cur.fetchall()
        expected_result = [(['hgjh', 'jj'],)]
        if res1 != expected_result:
            raise Exception("expected to get {}, instead got {}".format(expected_result, res1))
        Logger().info(res1)
        cur.close()

        #third test
        cur = self.con.cursor()
        cur.execute("select Array['2024-02-01 01:01:01' :: datetime]")
        res1 = cur.fetchall()
        expected_result = [([datetime(2024, 2, 1, 1, 1, 1)],)]
        if res1 != expected_result:
            raise Exception("expected to get {}, instead got {}".format(expected_result, res1))
        Logger().info(res1)
        cur.close()

        #fourth test
        cur = self.con.cursor()
        cur.execute("select Array['2024-02-01' :: date]")
        res1 = cur.fetchall()
        expected_result = [([date(2024, 2, 1), ],)]
        if res1 != expected_result:
            raise Exception("expected to get {}, instead got {}".format(expected_result, res1))
        Logger().info(res1)
        cur.close()

    def test_cursor(self):

        Logger().info("Cursor tests - running two statements on the same cursor connection")
        vals = [1]
        cur = self.con.cursor()
        cur.execute("select 1")
        res1 = cur.fetchall()[0][0]
        cur.close()
        vals.append(res1)
        cur = self.con.cursor()
        cur.execute("select 1")
        res2 = cur.fetchall()[0][0]
        vals.append(res2)
        if not all(x == vals[0] for x in vals):
            raise Exception(f"expected to get result 1, instead got {res1} and {res2}")
        cur.close()
        # todo - need to check
        # Logger().info("Cursor tests - running a statement through cursor when there is an open statement")
        # cur = self.con.cursor()
        # cur.execute("select 1")
        # sleep(10)
        # cur.execute("select 1")
        # res = cur.fetchall()[0][0]
        # if res != 1:
        #     raise Exception(f"expected to get result 1, instead got {res}")

        Logger().info("Cursor tests - fetch functions after all the data has already been read through cursor")
        self.execute("create or replace table test (xint int)")
        # network insert not supported
        # cur.executemany('insert into test values (?)', [(1,)])
        self.execute('insert into test values (1)')
        cur = self.con.cursor()
        cur.execute("select * from test")
        x = cur.fetchone()[0]
        res = cur.fetchone()
        if res is not None:
            raise Exception("expected to get an empty result from fetchone, instead got {}".format(res))
        try:
            cur.fetchall()
        except Exception as e:
            if "No open statement while attempting fetch operation" not in repr(e):
                raise Exception(f'bad error message')

        try:
            cur.fetchmany(1)
        except Exception as e:
            if "No open statement while attempting fetch operation" not in repr(e):
                raise Exception(f'bad error message')
        cur.close()

        Logger().info("Cursor tests - run a query through a cursor and close the connection directly")
        cur = self.con.cursor()
        cur.execute("select 1")
        self.con.close()
        if not self.con.connected:
            raise Exception(f'Closed a connection after running a query through a cursor, but cursor is still open')


class TestString(TestBase):

    def test_string(self):

        # network insert not supported
        # Logger().info("String tests - insert and return UTF-8")
        # self.con.execute("create or replace table test (xvarchar varchar(20))")
        # self.con.executemany('insert into test values (?)', [(u"hello world",), ("hello world",)])
        # self.con.execute("select * from test")
        # res = self.con.fetchall()
        # if res[0][0] != res[1][0]:
        #     raise Exception("expected to get identical strings from select statement. instead got {} and {}".format(res[0][0], res[1][0]))

        Logger().info("String tests - strings with escaped characters")
        self.execute("create or replace table test (xvarchar varchar(20))")
        values = [("\t",), ("\n",), ("\\n",), ("\\\n",), (" \\",), ("\\\\",), (" \nt",), ("'abd''ef'",), ("abd""ef",), ("abd\"ef",)]
        # network insert not supported
        # self.con.executemany('insert into test values (?)', values)
        for val in values:
            self.execute(f"insert into test values ($${val[0]}$$)")
        cur = self.con.cursor()
        cur.execute("select * from test")
        expected_list = [v[0] for v in values]
        res_list = []
        res_list += [x[0] for x in cur.fetchall()]
        if expected_list != res_list:
            raise Exception("expected to get {}, instead got {}".format(expected_list, res_list))
        cur.close()


class TestDatetime(TestBase):

    def test_datetime(self):
        Logger().info("Datetime tests - insert different timezones datetime")
        t1 = datetime.strptime(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), '%Y-%m-%d %H:%M')
        t2 = datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M"), '%Y-%m-%d %H:%M')
        self.execute("create or replace table test (xdatetime datetime)")
        # network insert not supported
        # self.concon.executemany('insert into test values (?)', [(t1,), (t2,)])
        self.execute(f'insert into test values ($${t1}$$)')
        self.execute(f'insert into test values ($${t2}$$)')
        res = self.fetch("select * from test")
        if res[0][0] == res[1][0]:
            raise Exception("expected to get different datetimes")

        Logger().info("Datetime tests - insert datetime with microseconds")
        t1 = datetime(1997, 5, 9, 4, 30, 10, 123456)
        t2 = datetime(1997, 5, 9, 4, 30, 10, 987654)
        self.execute("create or replace table test (xdatetime datetime)")
        # network insert not supported
        # self.con.executemany('insert into test values (?)', [(t1,), (t2,)])
        self.execute(f'insert into test values ($${t1}$$)')
        self.execute(f'insert into test values ($${t2}$$)')
        res = self.fetch("select * from test")
        if res[0][0] == res[1][0]:
            raise Exception("expected to get different datetimes")


# class TestTimeout(TestBaseWithoutBeforeAfter):
#     def test_timeout(self):
#         con = None
#         try:
#             Logger().info("test_timeout after 120 seconds")
#             con = pysqream_blue.connect(host=self.domain, use_ssl=False, query_timeout=120, access_token=self.access_token)
#             cur = con.cursor()
#             cur.execute("select sleep(200)")
#         except Exception as e:
#             if "Connection timeout expired" not in repr(e):
#                 raise Exception(f'bad error message')
#         finally:
#             if con is not None:
#                 con.close()


# class TestNoTimeout(TestBaseWithoutBeforeAfter):
#
#     def test_no_timeout(self):
#         con = None
#         try:
#             Logger().info("test_no_timeout")
#             start_time = datetime.now()
#             Logger().info(start_time)
#             con = pysqream_blue.connect(host=self.domain, use_ssl=False, access_token=self.access_token)
#             cur = con.cursor()
#             cur.execute("select sleep(200)")
#             end_time = datetime.now()
#             Logger().info(end_time)
#             delta = end_time - start_time
#             if delta.seconds < 200:
#                 raise ValueError("TimeOut occurs without reason!")
#         except Exception as e:
#             Logger().error(f"An error occurred {e}")
#             raise Exception(f"An error occurred {e}")
#         finally:
#             if con is not None:
#                 con.close()


class TestAbort(TestBase):

    def test_abort(self):
        cur = self.con.cursor()
        # try:
        #     Logger().info("Abort test - Prepare data before testing")
        #     create_query = "create or replace table big_text (x text)"
        #     insert_query1 = "insert into big_text values ('abcdef')"
        #     insert_query2 = "insert into big_text values ('eflmg')"
        #     insert_as_select_query = "insert into big_text select * from big_text"
        #     Logger().info(create_query)
        #     self.execute(create_query)
        #     Logger().info(insert_query1)
        #     self.execute(insert_query1)
        #     Logger().info(insert_query2)
        #     self.execute(insert_query2)
        #     for i in range(15):
        #         Logger().info(insert_as_select_query)
        #         self.execute(insert_as_select_query)
        #
        #     Logger().info("Abort test - Abort Query on fetch test")
        #     select_fetch_query = "select * from big_text where x like '%ef%'"
        #     Logger().info(select_fetch_query)
        #
        #     cur.execute(select_fetch_query)
        #     t = threading.Thread(target=cur.fetchall)
        #     t.start()
        #     time.sleep(5)
        #     cancel_response = cur.cancel()
        #     if not cancel_response:
        #         raise ValueError("Can't abort query on fetch")
        # except Exception as e:
        #     Logger().error(f"An error occurred {e}")
        # finally:
        #     cur.close()
        #     drop_query = "drop table big_text"
        #     Logger().info(drop_query)
        #     self.execute(drop_query)

        # Logger().info("Abort test - Abort Query on execute test")
        # select_sleep = "select sleep(200)"
        # Logger().info(select_sleep)
        # t1 = threading.Thread(target=cur.execute, args=(select_sleep,))
        # t1.start()
        # time.sleep(5)
        # cancel_response = cur.cancel()
        # if not cancel_response:
        #     raise ValueError("Can't abort query on execute")

        # Logger().info("Abort test - Abort Query on close statement")
        # select_1 = "select 1"
        # Logger().info(select_1)
        # cur = self.con.cursor()
        # cur.execute(select_1)
        # cur.fetchall()
        # try:
        #     cur.cancel()
        # except Exception as e:
        #     expected_error = "Query [{}] already closed"
        #     if expected_error not in repr(e):
        #         raise ValueError(f"expected to get {expected_error}, instead got {e}")
        # finally:
        #     cur.close()

        Logger().info("Abort test - Abort Query on close session test")

        self.con.close()
        try:
            cur.cancel()
        except Exception as e:
            expected_error = "Query [{}] already closed"
            if expected_error not in repr(e):
                raise ValueError(f"expected to get {expected_error}, instead got {e}")

        # TODO - add test for two queries on parallel on the same session and abort one of them after refactor


class TestThreads(TestBase):

    def _execute(self, num):

        cur = self.con.cursor()
        cur.execute("select {}".format(num))
        res = cur.fetchall()
        q.put(res)
        cur.close()

    def test_threads(self):

        Logger().info("Thread tests - concurrent inserts with multiple threads through cursor")
        t1 = threading.Thread(target=self._execute, args=(3, ))
        t2 = threading.Thread(target=self._execute, args=(3, ))
        t1.start()
        t2.start()
        res1 = q.get()[0][0]
        res2 = q.get()[0][0]
        if res1 != res2:
            raise Exception("expected to get equal values. instead got res1 {} and res2 {}".format(res1, res2))
