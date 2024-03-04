import sqlite3

class DbHandler:
    def __init__(self, print_queries = False):
        self.__conn = sqlite3.connect('8ball.db', check_same_thread=False)
        self.__conn.row_factory = sqlite3.Row
        self.__create_ball_table()
        self.__create_user_table()
        self.__conn.commit()
        self.__print_queries = print_queries
    
    def __create_user_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS "User" (_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Email TEXT NOT NULL UNIQUE,
        CreatedOn Date DEFAULT CURRENT_DATE,
        Ball_Id INTEGER FOREIGNKEY REFERENCES Ball(_id)
        );
        """
        self.__conn.execute(query)

    def __create_ball_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS "Ball" (_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ResponseYes TEXT,
        ResponseNo TEXT,
        ResponseUnknown TEXT,
        CreatedOn Date DEFAULT CURRENT_DATE
        );
        """
        self.__conn.execute(query)
    

    def get_user(self, properties_to_get: list[str], **conditions: str) -> list:
        """
        Obtains the data of every user that fits the given conditions

        Parameter properties_to_get: A list of columns to collect from matching rows.

        Prameter conditions: A dictionary of strings. Every key is a column, and for each table row, their value for that column must match the value paired with that key.
        """ 
        return self.__select("User", properties_to_get, **conditions)
    
    def __parse_conditions(self, prefix = "", suffix = "", connector = " AND ", **conditions: str | None) -> str:
        """
        Takes a map of conditions and creates a stringified query to be used in SQL commands.

        Parameter prefix: A string value to be added to the beginning of the return value before the main part of the string

        Parameter suffix: A string value to be added to the end of the return value after the main part of the string

        Parameter connector: A string value inserted between every stringified entry in the main part of the string.

        Parameter conditions: A dictionary of strings composing the main part of the string. Every key is a column which is set to be equal to its paired value.
        """
        if (len(conditions) == 0): return ""
        condition_list = []
        for column, value in conditions.items():
            if value is None:
                condition_list.append(column + ' = NULL')
            else:
                condition_list.append(column + ' = "' + str(value) + '"')
        return prefix + connector.join(condition_list) + suffix


    def __select(self, table: str, properties_to_get: list[str] | None = None, connector = " AND ", **conditions: str) -> list:
        """
        Executes a SELECT query and returns a 2-D list of all matching rows

        Parameter table: The name of the table to query.

        Parameter properties_to_get: A list of columns to collect from matching rows.

        Parameter connector: A string used to connect search conditions by AND or OR.

        Parameter conditions: A dictionary of strings. Every key is a column, and for each table row, their value for that column must match the value paired with that key.
        """
        table_indicators = self.__get_table_properties(properties_to_get)
        query = "SELECT " + table_indicators + " FROM " + table + self.__parse_conditions(prefix=" WHERE (", suffix=")", connector=connector, **conditions)
        if self.__print_queries: print(query)
        return self.__conn.execute(query).fetchall()
    
    def __insert(self, table: str, commit = True, add_quotes = True, **properties: str | None) -> int | None: 
        """
        Executes an INSERT command. If successful, the new row's ID number is returned. None if failed.

        Parameter table: The name of the table to insert a new row.

        Parameter commit: Indicates if a commit should immmediately follow a successful insertion of the row.

        Parameter add_quotes: Indicates if all values within the properties dictionary should be surrounded with quote marks.

        Parameter properties: A dictionary of strings. Every key is a column and is assigned its paired value in the new row.
        """
        keys, values = self.__split_dict(properties, add_quotes_in_values=add_quotes)
        query = "INSERT INTO " + table + " (" + keys + ") VALUES (" + values + ")"
        try:
            if self.__print_queries: print(query)
            cursor = self.__conn.execute(query)
            if commit: self.__conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            self.__conn.rollback()
            return None
        
    def __update(self, table: str, row_id: int | str, commit = True, **properties) -> bool:
        """
        Executes an UPDATE command. Returns true if successful, false if not

        Parameter table: The name of the table to change rows.

        Parameter row_id: The ID of the row to alter column data.

        Parameter commit: Indicates if a commit should immmediately follow a successful update of the row.

        Parameter properties: A dictionary of strings. Every key is a column and is re-assigned its paired value in the row.
        """
        query = "UPDATE " + table + " SET " + self.__parse_conditions(connector=", ", **properties) + " WHERE _id = " + str(row_id)
        try:
            if self.__print_queries: print(query)
            self.__conn.execute(query)
            if commit: self.__conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.__conn.rollback()
            return False
        
    def __delete(self, table: str, commit = True, **properties) -> bool:
        """
        Executes a DELETE command. Returns true if successful, false if not

        Parameter table: The name of the table to delete rows.

        Parameter commit: Indicates if a commit should immmediately follow a successful deletion of rows.

        Parameter properties: A dictionary of strings. Every key is a column and every column must match its paired value to delete the row
        """
        query = "DELETE FROM " + table + self.__parse_conditions(prefix=" WHERE (", suffix=")", **properties)
        try:
            if self.__print_queries: print(query)
            self.__conn.execute(query)
            if commit: self.__conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.__conn.rollback()
            return False
    
    def add_user(self, email: str):
        """
        Wrapper function for adding a new user to the table.
        """
        return self.__insert("User", Email=email)

    def __create_ball(self, user_id: int | str, add_defaults=True) -> int | None:
        """
        Creates a new Magic 8-Ball and adds it to the row of the given user.
        If successful, the ball's ID is returned. None if not.

        Parameter user_id: The ID of the user who wants a new 8-ball. Their row will be updated with the new ball ID

        Parameter add_defaults: If true, a few default phrases will be set to the new ball. If false, the new ball will be empty.
        """
        if add_defaults:
            defaults = {
                "ResponseYes": "Yes, definitely.;It is decidedly so.;You may rely on it.",
                "ResponseNo": "Signs point to no.;Don't count on it.;Definitely not.",
                "ResponseUnknown": "Maybe?;Try again.;Ask again later."
            }
        else:
            defaults = {
                "ResponseYes": None,
                "ResponseNo": None,
                "ResponseUnknown": None
            }
        
        id = self.__insert("Ball", commit=False, add_quotes=add_defaults, **defaults)
        
        if id is None: return None

        success = self.__update("User", user_id, commit=True, Ball_id=id)
        return id if success else None
    
    
    def get_ball(self, user_email: str, add_defaults_to_new=True) -> int | None:
        """
        Obtains the ID of the user's 8-ball (existing or newly created) and returns it if successful, None if not.

        Parameter user_email: The email of the user that wants an 8-ball.

        Parameter add_defaults_to_new: If true, indicates that if a new ball is being created, add default phrases to it.
        """
        users = self.get_user(["_id","Ball_Id"], email = user_email)
        if len(users) == 0: return None

        user_id, ball_id = users[0]

        if ball_id is None:
            return self.__create_ball(user_id, add_defaults_to_new)
        return int(ball_id)
    
    def get_answers(self, user_email: str, properties: list[str]) -> list[list[str] | None] | None:
        """
        Obtains all requested phrases from the user's 8-ball.

        Parameter user_email: The email of the user requesting phrases

        Parameter properties: A list of columns to search for phrases.

        Returns a 2-D list of strings, or None if the search failed.
        The nested lists are in order of the columns provided in the properties parameter.
        If a column held a null value, its nested list will be None.
        """
        ball_id = self.get_ball(user_email)
        if ball_id is None: return None

        row = self.__select("Ball", properties, _id = ball_id)[0]
        
        send: list[list[str] | None] = []
        
        for delimited_string in row:
            send.append(None if delimited_string is None else delimited_string.split(";"))
        return send
    

    def add_answers(self, user_email: str, messages: dict[str, list[str]]) -> dict[str, list[str]] | None:
        """
        Appends a set of user-provided phrases to the 8-ball's lists

        Parameter user_email: The email of the user adding phrases

        Parameter messages: A dictionary of string lists. Each key is a category of Yes, No or Unkonwn, and each value is a list of strings to append to that category.

        Returns a dictionary of strings, or None if the attempt failed.
        The keys are the same as the user-provided dictionary, and the lists have all the new phrases that were inserted into the 8-ball
        """
        ball_id = self.get_ball(user_email, False)
        if (ball_id is None): return None

        existing_answers_map: list[str | None] = self.__select("Ball", ["ResponseYes", "ResponseNo", "ResponseUnknown"], _id = ball_id)[0]

        existing_answers_map = [[] if array is None else array.split(";") for array in existing_answers_map]

        response = dict()
        new_data = dict()

        index = 0

        for column, array in messages.items():
            column_response = set()
            existing_answers = existing_answers_map[index]
            for entry in array:
                if entry in existing_answers: continue

                column_response.add(entry)
                existing_answers.append(entry)
            response[column.removeprefix("Response")] = list(column_response)
            new_data[column] = ";".join(existing_answers)
            index += 1

        success = self.__update("Ball", ball_id, **new_data)
        return response if success else None
        

    def delete_answers(self, user_email: str, category: str) -> bool | None:
        """
        Erases the given category's list of phrases from the user's 8ball
        Returns true if successful, False if the update failed, None if no user or ball was found.
        """
        users = self.get_user(["_id","Ball_id"], email = user_email)
        if len(users) == 0: return None

        _,  ball_id = users[0]
        if ball_id is None: return None

        conditions = dict()
        conditions[category] = None
        return self.__update("Ball", ball_id, **conditions)

        
    
    def __get_table_properties(self, properties, include_quotes = False) -> str:
        """
        Stringifies and returns a collection of properties, delimiting them by a comma and space
        if include_quotes is true, each stringified item will be surrounded by quote marks.
        """
        if properties is None or len(properties) == 0:
            return "*"
        delimiter = "\", \"" if include_quotes else ", "
        send = delimiter.join(properties)
        if include_quotes:
            send = '"' + send + '"'
        return send
    
    def __split_dict(self, dict: dict[str, str], to_string = True, add_quotes_in_values = True) -> tuple[str,str] | tuple[list[str],list[str]]:
        """
        Takes a given dictionary and splits their keys and values into two different collections, returning them.
        
        Parameter dict: the dictionary to split.

        Parameter to_string: if true, the collections are stringified and then returned. If false, the collections are returned as lists.

        Prameter add_quotes_in_values: if true, the strings inside the values collection will be surrounded with quote marks. This does not stringify the list itself

        """
        keys = []
        values = []
        for key, value in dict.items():
            keys.append(key)
            values.append("NULL" if value is None else value)
        if to_string:
            return (self.__get_table_properties(keys),self.__get_table_properties(values,add_quotes_in_values))
        if add_quotes_in_values:
            values = ["NULL" if v is None else '"' + str(v) + '"' for v in values]
        return (keys, values)


    def delete_ball(self, user_email: str) -> bool | None:
        """
        Deletes the ball record that belongs to a given user.
        Returns true if successful, false if the deletion failed, None if the user or ball was not found.
        """
        users = self.get_user(["_id","Ball_id"], email = user_email)
        if len(users) == 0: return None

        user_id, ball_id = users[0]
        if ball_id is None: return True

        success = self.__delete("Ball", commit=False, _id = ball_id)
        if not success: return False

        return self.__update("User", user_id, Ball_id = None)
    
    