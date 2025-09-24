import shutil
import sqlite3 as sq

def create_database():
    occasions_tb = """
    CREATE TABLE IF NOT EXISTS occasions 
    (occasion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    occasion_name TEXT NOT NULL,
    total_spent INTEGER CHECK (total_spent >= 0),
    right_amount INTEGER CHECK (right_amount >= 0))
    """

    people_tb = """
    CREATE TABLE IF NOT EXISTS people 
    (person_id INTEGER PRIMARY KEY AUTOINCREMENT, 
    person_name TEXT NOT NULL,
    initial_amount INTEGER CHECK (initial_amount >= 0), 
    final_amount INTEGER CHECK (final_amount >= 0),
    occasion_id INTEGER NOT NULL,
    FOREIGN KEY (occasion_id) REFERENCES occasions (occasion_id)
    )
    """

    items_tb = """ 
    CREATE TABLE IF NOT EXISTS items
    (item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    item_price INTEGER CHECK (item_price > 0),
    person_id INTEGER NOT NULL,
    occasion_id INTEGER NOT NULL,
    FOREIGN KEY (person_id) REFERENCES people (person_id),
    FOREIGN KEY (occasion_id) REFERENCES occasions(occasion_id)
    )
    """

    transactions_tb = """
    CREATE TABLE IF NOT EXISTS transactions
    (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    amount INTEGER CHECK (amount > 0),
    occasion_id INTEGER NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES people (person_id),
    FOREIGN KEY (receiver_id) REFERENCES people (person_id),
    FOREIGN KEY (occasion_id) REFERENCES occasions(occasion_id)
    )
    """

    cursor.execute(occasions_tb)
    cursor.execute(people_tb)
    cursor.execute(items_tb)
    cursor.execute(transactions_tb)
    connection.commit()
    
def create_triggers():
    """Add triggers to the database to perform some calculations automatically once relevant data has been added."""
    
    # after items have been added, calculate the total amount spent
    count_total = """ CREATE TRIGGER IF NOT EXISTS count_total
    AFTER INSERT ON items
    BEGIN
    UPDATE occasions SET total_spent = total_spent + NEW.item_price
    WHERE occasion_id = NEW.occasion_id;
    END;
    """
    
    # after items have been added, calculate the initial amount spent by each person
    count_initial = """ CREATE TRIGGER IF NOT EXISTS count_initial
    AFTER INSERT ON items
    BEGIN
    UPDATE people SET initial_amount = initial_amount + NEW.item_price
    WHERE person_id = NEW.person_id;
    UPDATE people SET final_amount = initial_amount
    WHERE occasion_id = NEW.occasion_id;
    END;
    """
    
    # after transactions have been added, calculate the final amount spent by each person
    calc_final = """ CREATE TRIGGER IF NOT EXISTS calc_final
    AFTER INSERT ON transactions
    BEGIN
    UPDATE people SET final_amount = final_amount + NEW.amount
    WHERE person_id = NEW.sender_id;
    UPDATE people SET final_amount = final_amount - NEW.amount
    WHERE person_id = NEW.receiver_id;
    END;
    """

    cursor.execute(count_total)
    cursor.execute(count_initial)
    cursor.execute(calc_final)
    connection.commit()
    
def data_from_file(filename):
    """Reading data from file and creating three variables: occasion (str), people (list) and items (dict)"""
    
    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found.")

    items = {}

    for num in range(len(lines)):
        if lines[num].strip() == "Occasion:":
            occasion = lines[num + 1].strip()

        elif lines[num].strip() == "People:":
            people_start = num + 1

        elif lines[num].strip() == "Items:":
            people_end = num
            items_start = num + 1

    items_end = len(lines)
    people = [lines[num].strip() for num in range(people_start, people_end)]

    for num in range(items_start, items_end):
        item = lines[num].strip().split(" - ")
        item_name = item[0]
        buyer_name = item[1]
        price = int(item[2])
        items[item_name] = (price, buyer_name)  
    return occasion, people, items

def add_occasion(occasion):
    """Add new occasion to the database. An occasion is only accepted if it's not in the database yet."""
    
    check_occasions = f""" SELECT occasion_name FROM occasions """
    cursor.execute(check_occasions)
    all_occasions = [occ[0] for occ in cursor.fetchall()]
    if occasion in all_occasions:
        raise Exception("There's already an occasion with this name in the database. Please choose a different name")
    else:
        new_occasion = (occasion, 0)
        request_to_insert = """ INSERT INTO occasions (occasion_name, total_spent) VALUES (?, ?); """
        cursor.execute(request_to_insert, new_occasion)
        connection.commit()

def get_occasion_id(occasion_name):
    """ Takes occasion_name (str) and returns occasion_id(int) """
    
    find_occasion_id = f"""
    SELECT occasion_id FROM occasions WHERE occasion_name = "{occasion_name}"
    """
    cursor.execute(find_occasion_id)
    occasion_id = cursor.fetchall()[0][0]
    return occasion_id

def add_people(people, occasion_id):
    for name in people:
        new_person = (name, occasion_id, 0)
        request_to_insert = """ INSERT INTO people (person_name, occasion_id, initial_amount) VALUES (?, ?, ?); """
        cursor.execute(request_to_insert, new_person)
        connection.commit()
        
def find_num_people(occasion_id):
    """ Takes occasion_id (int) and returns number of people involved (int) """
    
    find_num_people = f""" SELECT person_name from people WHERE occasion_id = "{occasion_id}" """
    cursor.execute(find_num_people)
    num_people = len(cursor.fetchall())
    return num_people

def add_items(items, occasion_id):
    for item in items.items():
        name = item[0]
        price = item[1][0]
        buyer = item[1][1]

        find_person_id = f""" SELECT person_id FROM people WHERE person_name = "{buyer}" AND occasion_id = {occasion_id} """
        cursor.execute(find_person_id)
        person_id = cursor.fetchall()[0][0]

        new_item = (name, price, person_id, occasion_id)
        request_to_insert = """ INSERT INTO items (item_name, item_price, person_id, occasion_id) VALUES (?, ?, ?, ?); """
        cursor.execute(request_to_insert, new_item)
        connection.commit()
        
def calc_right_amount(occasion_id, num_people):
    find_total_spent = f""" SELECT total_spent FROM occasions WHERE occasion_id = {occasion_id} """
    cursor.execute(find_total_spent)
    total_spent = cursor.fetchall()[0][0]
    right_amount = round(total_spent / num_people)
    return right_amount

def add_right_amount(occasion_id, right_amount):
    update_right_amount = """ UPDATE occasions SET right_amount = ? WHERE occasion_id = ? """
    cursor.execute(update_right_amount, (right_amount, occasion_id))
    connection.commit()
    
def create_names_amounts(occasion_id):
    """Sort people by the initial amount they have spent.
    
    Creates a dictionary names_amounts and sorts it from largest to smallest amount spent.
    Example: {4: 2200, 3: 1600, 2: 1000, 1: 200}. Keys are people's ids and values are their initial amount spent.
    """
    select_people = f""" SELECT person_id, initial_amount FROM people WHERE occasion_id = {occasion_id} """
    cursor.execute(select_people)
    names_amounts = {person[0]: person[1] for person in cursor.fetchall()}
    names_amounts = dict(sorted(names_amounts.items(), key=lambda item: item[1], reverse=True))
    return names_amounts
        

def calc(names_amounts):
    """Calculate who should send how much to whom to make sure everyone spends the same amount.
    
    Takes a dictionary names_amounts with the initial amount spent by each person
    and returns dictionary who_sends_what with all the necessary transactions.
    
    Input example: {4: 2200, 3: 1600, 2: 1000, 1: 200}.
    Output example: {3: [[4, 150]], 2: [[3, 150], [4, 300]], 1: [[2, 200], [3, 350], [4, 500]]}.
    Keys are sender ids, values are lists of integers where the first integer is receiver id
    and the second is the amount that should be sent.
    """
    # calculating parts (amount spent divided by number of people) for each person and adding them to the dictionary
    for person in names_amounts.items():
        person_id = person[0]
        current_amount = person[1]
        part = round(current_amount / len(names_amounts))
        names_amounts[person_id] = [current_amount, part]
    
    item_list = list(names_amounts.items())
    who_sends_what = {}
    
    # everyone only sends money to those who come before them in the dictionary.
    # range starts with 1 so that it doesn't include the first person - they've spent the most and don't need to send anything
    for num in range(1, len(names_amounts)):
        curr_person = item_list[num]
        curr_id = curr_person[0]
        curr_part = curr_person[1][1]
        prev_people_amount = []
        
        for num2 in range(num-1, -1, -1):
            prev_person = item_list[num2]
            prev_id = prev_person[0]
            prev_part = prev_person[1][1]
            to_send = prev_part - curr_part
            prev_people_amount.append([prev_id, to_send])
        who_sends_what[curr_id] = prev_people_amount
    return who_sends_what
    
def add_transactions(who_sends_what, occasion_id):
    add_transaction = """ INSERT INTO transactions (sender_id, receiver_id, amount, occasion_id) VALUES (?, ?, ?, ?); """
    for item in who_sends_what.items():
        sender = item[0]
        transactions = item[1]
        for transaction in transactions:
            receiver = transaction[0]
            amount = transaction[1]
            if amount:
                result = (sender, receiver, amount, occasion_id)
                cursor.execute(add_transaction, result)
                connection.commit()
            
def check(occasion_id, right_amount):
    """Make sure the final amount spent by each person is close to the right amount."""
    
    select_final_amounts = f""" SELECT person_id, final_amount FROM people WHERE occasion_id = {occasion_id}"""
    cursor.execute(select_final_amounts)
    ids_final_amounts = {person[0]: person[1] for person in cursor.fetchall()}
    for person in ids_final_amounts.items():
        if person[1] in range(right_amount - 2, right_amount + 3):
            print("Everything seems right.")
        else:
            print(f"""Something is wrong with person {person[0]}, 
                  their final amount is {[person[1]]}, but it should be {right_amount}""")
            
def result(original_file, new_file, who_sends_what, occasion_id, num_people, right_amount):
    """Create a text file with the result.
    
    Creates a copy of the input file and adds instructions on who should send how much to whom. 
    Also adds an explanation.
    """
    
    try:
        shutil.copyfile(original_file, new_file)
    except FileNotFoundError:
        print(f"Error: File '{original_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    try:
        with open(new_file, "a") as file:
            file.write("\n\nOverview:")
            select_total = f""" SELECT total_spent FROM occasions WHERE occasion_id = {occasion_id}"""
            find_total = cursor.execute(select_total)
            total = cursor.fetchall()[0][0]
            file.write(f"\nTotal spent is {total}.")
            file.write(f"\nThere are {num_people} people, so each should spend {right_amount}.")
            
            select_name_initial = f""" SELECT person_name, initial_amount FROM people WHERE occasion_id = {occasion_id} """
            cursor.execute(select_name_initial)
            names_initials = cursor.fetchall()
            length = len(names_initials)
            for num in range(length):
                name = names_initials[num][0]
                amount = names_initials[num][1]
                if num == 0:
                    file.write(f"\n\nInitially, {name} has spent {amount}, ")
                elif num == length - 1:
                    file.write(f"{name} {amount}.")
                else:
                    file.write(f"{name} {amount}, ")
            
            file.write("\n\nTo do:")
            select_transactions = f""" SELECT sender_id, receiver_id, amount FROM transactions where occasion_id = {occasion_id} """
            cursor.execute(select_transactions)
            all_transactions = [item for item in cursor.fetchall()]
            
            select_name = """ SELECT person_name FROM people WHERE person_id = ? """
            
            for item in all_transactions:
                sender_id = item[0]
                receiver_id = item[1]
                amount = item[2]
                
                find_sender_name = cursor.execute(select_name, (sender_id, ))
                sender_name = cursor.fetchall()[0][0]
                
                find_receiver_name = cursor.execute(select_name, (receiver_id, ))
                receiver_name = cursor.fetchall()[0][0]
                file.write(f"\n{sender_name} sends {amount} to {receiver_name}")
                    
            file.write("\n\nExplanation:")
            select_ids_names_final = f""" SELECT person_id, person_name, final_amount FROM people where occasion_id = {occasion_id} """
            cursor.execute(select_ids_names_final)
            all_ids_names = cursor.fetchall()
            
            for person in all_ids_names:
                person_id = person[0]
                person_name = person[1]
                final_amount = person[2]
                file.write(f"\n{person_name}'s expenses:")
                for item in names_initials:
                    if person_name in item:
                        initial = item[1]
                        file.write(f" {initial}")
                for item in all_transactions:
                    if person_id in item:
                        sender = item[0]
                        receiver = item[1]
                        amount = item[2]
                        if person_id == sender:
                            file.write(f" + {amount}")
                        elif person_id == receiver:
                            file.write(f" - {amount}")
                file.write(f" = {final_amount}\n")
            
    except FileNotFoundError:
            print(f"Error: The file {newfile} was not found.")
            
def run(filename):
    # connecting to the database and creating it
    create_database()
    create_triggers()
    
    # reading data from file
    occasion, people, items = data_from_file(filename)
    
    # adding a new occasion
    add_occasion(occasion)
    occasion_id = get_occasion_id(occasion)
    
    # adding people and items
    add_people(people, occasion_id)
    add_items(items, occasion_id)
    
    # finding the number of people
    num_people = find_num_people(occasion_id)
    
    # finding the right amount
    right_amount = calc_right_amount(occasion_id, num_people)
    add_right_amount(occasion_id, right_amount)
    
    # creating a names_amounts dictionary.
    names_amounts = create_names_amounts(occasion_id)
    
    # calculating transactions based on names_amounts
    who_sends_what = calc(names_amounts)
    add_transactions(who_sends_what, occasion_id)
    
    # checking whether the final amount is close to the right amount (+-2)
    check(occasion_id, right_amount)
    
    # writing results to a new file
    result(filename, f'{filename}_result.txt', who_sends_what, occasion_id, num_people, right_amount)
    
if __name__ == "__main__":
    filename = input("Please, type in a filename. ").strip()
    connection = sq.connect('presents_database.db')
    cursor = connection.cursor()
    run(filename)
    cursor.close()
    connection.close()

